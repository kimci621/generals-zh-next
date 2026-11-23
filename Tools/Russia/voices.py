# /// script
# requires-python = ">=3.12"
# dependencies = ["mlx-audio", "soundfile", "faster-whisper", "numpy"]
# ///
"""Озвучка юнитов России: Qwen3-TTS VoiceDesign (Apache-2.0, MLX) -> ffmpeg -> wav + AudioEvent'ы + патчи объектов.

    uv run Tools/Russia/voices.py --vanilla DIR [--only CODE] [--what units|eva|all] [--asr medium|none]

Голос задаётся текстовым описанием (род войск + характер юнита + эмоция реплики), сверху обработка
окружения по роду войск: пехота сухо, бронетехника через ТПУ с гулом двигателя, машины по рации,
авиация через кислородную маску. Каждая реплика распознаётся Whisper'ом; если текст не совпал
(сходство < MIN_SIM), синтез повторяется, берётся лучший из TRIES. Знак ударения модель не понимает,
поэтому слова с плавающим ударением ("связи", "исправна") в репликах не используются. Пишет:
  Data/Audio/Sounds/r<code><kind><letter>.wav    22050 Гц, моно, 16 бит, -16 LUFS (как у EA и Турции)
  Data/INI/VoiceReforged.ini                     AudioEvent'ы между маркерами RUSSIA VOICES
  Data/INI/RussiaReforged.ini                    Voice*/UnitSpecificSounds между маркерами RUSSIA VOICES
Исходные Voice-поля и UnitSpecificSounds берутся из ванильного INI (--vanilla, распакованный INIZH.big):
UnitSpecificSounds при патче очищается целиком, поэтому неголосовые записи копируются как есть.
"""
import argparse
import difflib
import glob
import os
import re
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "..", "..", "GeneralsMD", "Code", "Data")
BEGIN, END = ";; BEGIN RUSSIA VOICES by Tools/Russia/voices.py\n", ";; END RUSSIA VOICES\n"
MODEL = "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit"
# клонирование с эталона: VoiceDesign придумывает голос заново на каждой реплике, диктор должен быть один
CLONE = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
MIN_SIM, TRIES = 0.85, 4
KINDS = {"se": "Select", "mo": "Move", "at": "Attack", "fe": "Fear", "cr": "Create"}

# род войск -> (описание голоса, обработка ffmpeg, щелчки рации EA в событии)
CLS = {
    "inf": ("Male voice of an elite professional Russian soldier, {}. Calm, disciplined, confident, "
            "short precise military reports, quiet authority.",
            "highpass=f=90,acompressor=threshold=-20dB:ratio=4,aecho=0.8:0.3:12:0.15", False),
    "arm": ("Firm male voice of a professional Russian armored vehicle commander, {}, giving crisp orders "
            "over the intercom with a roaring engine. Loud, controlled, decisive, strictly by the book.",
            "TANK", True),
    "veh": ("Male voice of a professional Russian military vehicle crew member, {}, speaking on the radio. "
            "Composed, crisp, businesslike.",
            "highpass=f=300,lowpass=f=3400,acompressor=threshold=-22dB:ratio=5,acrusher=bits=12:mix=0.2", True),
    "air": ("Calm male voice of an experienced Russian military pilot, {}, on the radio. Steady breathing, "
            "clipped professional phrasing, absolute composure.",
            "highpass=f=350,lowpass=f=2800,acrusher=bits=10:mix=0.3,equalizer=f=1200:t=q:w=1:g=6", True),
}
# эталон голоса юнита: спокойная и боевая часть, чтобы клон умел и то, и другое
UNIT_REF = "Принял, выполняю. Внимание, контакт! Огонь, огонь!"
UNIT_REF_MOOD = "Starts calm and composed, then switches to intense and urgent combat shouting."
# танк: ТПУ с перегрузом + гул дизеля с вибрацией
TANK = ("[0]adelay=250,apad=pad_dur=0.35,highpass=f=300,lowpass=f=3200,acompressor=threshold=-24dB:ratio=6,"
        "acrusher=bits=8:mix=0.25,volume=2[v];[1]lowpass=f=140,tremolo=f=28:d=0.4,volume=1.2[e];"
        "[v][e]amix=inputs=2:duration=first:normalize=0,afade=t=in:d=0.15")

# объект: (код, род войск, характер голоса, реплики {вид: [...]})
U = {
    "InfantryMotorRifle": ("mot", "inf", "in his thirties, a seasoned contract sergeant", {
        "se": ["Отделение готово.", "Слушаю, командир.", "Мотострелки здесь.", "Жду приказа."],
        "mo": ["Принял. Выдвигаемся.", "Есть.", "Отделение, за мной.", "Выполняю."],
        "at": ["Огонь!", "Цель вижу. Работаем.", "Контакт! Огонь на подавление!", "Отделение, огонь!"],
        "fe": ["Плотный огонь! Укрыться!", "Отходим перекатами!"],
        "cr": ["Мотострелковое отделение прибыло."]}),
    "InfantryReservist": ("rez", "inf", "in his late forties, an older mobilized reservist, low and weathered but steady", {
        "se": ["Резерв на месте.", "Слушаю.", "Готов.", "Жду команды."],
        "mo": ["Принял.", "Есть.", "Выдвигаюсь.", "Понял, иду."],
        "at": ["Огонь!", "Стреляю!", "Цель вижу!", "Держим рубеж!"],
        "fe": ["Под огнём! Залечь!", "Отходим!"],
        "cr": ["Резервист прибыл."]}),
    "InfantryRPG": ("rpg", "inf", "in his twenties, an alert grenadier, slightly higher and sharper", {
        "se": ["Гранатомётчик.", "Слушаю.", "Готов.", "Найду любую броню."],
        "mo": ["Есть.", "Меняю позицию.", "Принял.", "Выдвигаюсь."],
        "at": ["Выстрел!", "Бью по броне!", "Гранатомёт, огонь!", "Попадание!"],
        "fe": ["Прижали! Укрыться!", "Назад!"],
        "cr": ["Гранатомётчик готов."]}),
    "InfantryVerba": ("vrb", "inf", "in his thirties, an air-defense gunner, focused and watchful", {
        "se": ["Расчёт Вербы.", "Небо под контролем.", "Слушаю.", "Готовы."],
        "mo": ["Перемещаемся.", "Есть.", "Принял.", "Выполняем."],
        "at": ["Пуск!", "Цель в воздухе!", "Захват есть. Пуск!", "Сбиваем!"],
        "fe": ["Нас накрыли!", "Отходим!"],
        "cr": ["Зенитный расчёт прибыл."]}),
    "InfantryEngineer": ("ing", "inf", "in his thirties, a combat engineer, practical and precise", {
        "se": ["Инженер.", "Что строим?", "Слушаю.", "Инструмент при мне."],
        "mo": ["Есть.", "Принял.", "Иду.", "Скоро буду."],
        "at": ["Работаю.", "Вскрываю.", "Минута, и готово.", "Приступаю."],
        "fe": ["Нужно прикрытие!", "Отхожу!"],
        "cr": ["Инженер прибыл."]}),
    "InfantryFPV": ("fpv", "inf", "in his twenties, a drone operator, quick and sharp", {
        "se": ["Оператор дрона.", "Птичка готова.", "Слушаю.", "На позиции."],
        "mo": ["Меняю точку.", "Принял.", "Иду.", "Есть."],
        "at": ["Запускаю!", "Птичка пошла!", "Цель вижу. Захожу!", "Есть попадание!"],
        "fe": ["Меня засекли!", "Уходим!"],
        "cr": ["Оператор дрона прибыл."]}),
    "InfantrySniper": ("snp", "inf", "in his forties, a sniper, very quiet, low, almost whispering, ice cold", {
        "se": ["Снайпер.", "Тихо.", "Вижу всё.", "Слушаю."],
        "mo": ["Меняю позицию.", "Принял.", "Ухожу.", "Есть."],
        "at": ["Цель.", "Один выстрел.", "Снимаю.", "Готово."],
        "fe": ["Раскрыт!", "Отход!"],
        "cr": ["Снайпер на позиции."]}),
    "InfantryKornet": ("krn", "inf", "in his thirties, an anti-tank missile team leader, steady and deliberate", {
        "se": ["Расчёт Корнета.", "Слушаю.", "Готовы.", "Ждём танки."],
        "mo": ["Перемещаемся.", "Есть.", "Принял.", "Выполняем."],
        "at": ["Пуск!", "Ракета пошла!", "Цель захвачена!", "Бьём танк!"],
        "fe": ["Под огнём!", "Отходим!"],
        "cr": ["Противотанковый расчёт прибыл."]}),
    "InfantryGRU": ("gru", "inf", "in his late thirties, a special forces operator, very low, calm and menacing", {
        "se": ["Спецназ.", "Слушаю.", "Работаем тихо.", "Готов."],
        "mo": ["Принял.", "Ухожу.", "Есть.", "Работаем."],
        "at": ["Работаю.", "Ликвидирую.", "Сделано.", "Вошёл."],
        "fe": ["Отход!", "Меня видят!"],
        "cr": ["Спецназ прибыл."]}),
    "VehicleIMR3M": ("imr", "arm", "an engineering vehicle commander, practical and steady", {
        "se": ["Инженерная машина.", "Что расчищаем?", "Слушаю.", "Готов к работе."],
        "mo": ["Двигаюсь.", "Принял.", "Начинаю.", "Есть."],
        "at": ["Расчищаю.", "Давлю.", "Работаю.", "Убираю завал."],
        "cr": ["Инженерная машина готова."]}),
    "VehicleKamaz": ("kmz", "veh", "a military truck driver, easygoing but disciplined", {
        "se": ["Камаз.", "Водитель слушает.", "Груз возим.", "Слушаю."],
        "mo": ["Еду.", "Принял.", "Поехали.", "Есть."],
        "at": ["Везу снабжение.", "Грузимся.", "Еду за грузом.", "Принял."],
        "cr": ["Камаз к работе готов."]}),
    "VehicleTOS2": ("tos", "veh", "a heavy flamethrower system commander, deep and grim", {
        "se": ["Тосочка.", "Огнемётная система.", "Слушаю.", "Готовы."],
        "mo": ["Выдвигаемся.", "Есть.", "Принял.", "Меняем позицию."],
        "at": ["Залп!", "Накрываем квадрат!", "Пуск!", "Огонь по площади!"],
        "cr": ["ТОС-2 готова."]}),
    "VehicleTOS1A": ("tsa", "arm", "a heavy flamethrower system commander, very deep, grim and heavy", {
        "se": ["Солнцепёк.", "Слушаю.", "Готовы.", "Огнемётная система."],
        "mo": ["Выдвигаемся.", "Есть.", "Принял.", "Идём."],
        "at": ["Залп!", "Квадрат накрыт!", "Огонь!", "Выжигаем!"],
        "cr": ["Солнцепёк готов."]}),
    "TankT72B3M": ("t72", "arm", "in his thirties, a veteran tank commander", {
        "se": ["Экипаж Т семьдесят два.", "Слушаю.", "Танк готов.", "Экипаж на месте."],
        "mo": ["Вперёд.", "Есть.", "Принял. Двигаюсь.", "Выполняю."],
        "at": ["Огонь!", "Выстрел!", "Цель поражена!", "Бронебойным! Огонь!"],
        "cr": ["Танк готов к бою."]}),
    "TankT90M": ("t90", "arm", "in his forties, a senior tank commander, deep and authoritative", {
        "se": ["Прорыв на месте.", "Слушаю.", "Экипаж готов.", "Т девяносто."],
        "mo": ["Вперёд.", "Есть.", "Двигаюсь.", "Принял."],
        "at": ["Огонь!", "Цель вижу!", "Выстрел!", "Поражение!"],
        "cr": ["Т девяносто к бою готов."]}),
    "TankT14": ("t14", "arm", "in his thirties, an elite tank commander, cool and technical", {
        "se": ["Армата.", "Слушаю.", "Экипаж готов.", "Системы в норме."],
        "mo": ["Вперёд.", "Есть.", "Принял.", "Выдвигаюсь."],
        "at": ["Огонь!", "Цель уничтожить!", "Выстрел!", "Подавляю!"],
        "cr": ["Армата готова."]}),
    "TankBMPT": ("bmt", "arm", "a fire support vehicle commander, aggressive and sharp", {
        "se": ["Терминатор.", "Слушаю.", "Готов.", "Экипаж на месте."],
        "mo": ["Есть.", "Двигаюсь.", "Принял.", "Вперёд."],
        "at": ["Огонь!", "Чешу пехоту!", "Подавляю!", "Работаю!"],
        "cr": ["Терминатор готов."]}),
    "VehicleBTR82A": ("btr", "arm", "an armored carrier commander, brisk and energetic", {
        "se": ["Бэтээр.", "Слушаю.", "Десант на борту.", "Готов."],
        "mo": ["Едем.", "Есть.", "Принял.", "Двигаюсь."],
        "at": ["Огонь!", "Работаю пушкой!", "Подавляю!", "Цель вижу!"],
        "cr": ["Бэтээр готов."]}),
    "VehicleBMP3": ("bmp", "arm", "an infantry fighting vehicle commander, steady", {
        "se": ["Бээмпэ.", "Слушаю.", "Готов.", "Экипаж на месте."],
        "mo": ["Едем.", "Есть.", "Принял.", "Вперёд."],
        "at": ["Огонь!", "Цель вижу!", "Работаю!", "Выстрел!"],
        "cr": ["Бээмпэ готова."]}),
    "VehicleTigrM": ("tgr", "veh", "in his twenties, a reconnaissance driver, quick and alert", {
        "se": ["Тигр.", "Слушаю.", "Готов.", "Разведка на месте."],
        "mo": ["Едем.", "Есть.", "Принял.", "Погнали."],
        "at": ["Огонь!", "Работаю!", "Вижу цель!", "Стреляю!"],
        "cr": ["Тигр готов."]}),
    "VehiclePantsir": ("pnc", "veh", "an air-defense system operator, focused and technical", {
        "se": ["Панцирь.", "Небо чистое.", "Слушаю.", "Готов."],
        "mo": ["Перемещаюсь.", "Есть.", "Принял.", "Выдвигаюсь."],
        "at": ["Пуск!", "Воздушная цель!", "Сбиваю!", "Огонь!"],
        "cr": ["Панцирь готов."]}),
    "VehicleTorM2": ("tor", "veh", "an air-defense system commander, older and measured", {
        "se": ["Тор.", "Слушаю.", "Небо под контролем.", "Готов."],
        "mo": ["Перемещаюсь.", "Есть.", "Принял.", "Выдвигаюсь."],
        "at": ["Пуск!", "Захват!", "Сбиваю!", "Цель!"],
        "cr": ["Тор готов."]}),
    "VehicleMstaS": ("mst", "arm", "an artillery battery commander, deep and methodical", {
        "se": ["Самоходка Мста.", "Слушаю.", "Орудие готово.", "Батарея ждёт."],
        "mo": ["Меняем позицию.", "Есть.", "Принял.", "Выдвигаемся."],
        "at": ["Выстрел!", "Огонь по квадрату!", "Орудие, огонь!", "Накрываем!"],
        "cr": ["Гаубица готова."]}),
    "VehicleTornadoG": ("trn", "veh", "a rocket artillery commander, firm and loud", {
        "se": ["Торнадо.", "Слушаю.", "Пакет готов.", "Батарея ждёт."],
        "mo": ["Меняем позицию.", "Есть.", "Принял.", "Едем."],
        "at": ["Залп!", "Пуск!", "Накрываем!", "Огонь!"],
        "cr": ["Торнадо готов."]}),
    "VehicleKrasukha": ("krs", "veh", "an electronic warfare officer, cool, technical and dry", {
        "se": ["Красуха.", "Эфир наш.", "Слушаю.", "Готов."],
        "mo": ["Перемещаюсь.", "Есть.", "Принял.", "Еду."],
        "at": ["Глушим.", "Помехи пошли.", "Давлю эфир.", "Работаю."],
        "cr": ["Красуха готова."]}),
    "VehicleLancet": ("lnc", "veh", "a loitering munition operator, quick and precise", {
        "se": ["Ланцет.", "Слушаю.", "Барражирую.", "Готов."],
        "mo": ["Есть.", "Принял.", "Перемещаюсь.", "Иду."],
        "at": ["Пуск!", "Цель!", "Захожу!", "Удар!"],
        "cr": ["Ланцет готов."]}),
    "JetSu25": ("s25", "air", "a ground attack pilot in his thirties, through an oxygen mask, tough and steady", {
        "se": ["Грач в эфире.", "Слушаю.", "Готов.", "Штурмовик."],
        "mo": ["Понял.", "Есть.", "Следую.", "Выполняю."],
        "at": ["Атакую!", "Захожу на цель!", "Пуск!", "Работаю!"],
        "cr": ["Грач к вылету готов."]}),
    "JetSu34": ("s34", "air", "a bomber pilot in his forties, through an oxygen mask, deep and measured", {
        "se": ["Бомбардировщик.", "Слушаю.", "Готов.", "Борт в эфире."],
        "mo": ["Понял.", "Есть.", "Следую.", "Выполняю."],
        "at": ["Сброс!", "Цель на прицеле!", "Бомбы пошли!", "Атакую!"],
        "cr": ["Су тридцать четыре готов."]}),
    "JetSu35": ("s35", "air", "a young fighter pilot, through an oxygen mask, sharp and cool", {
        "se": ["Истребитель.", "Слушаю.", "Небо наше.", "Борт в эфире."],
        "mo": ["Понял.", "Есть.", "Следую.", "Выполняю."],
        "at": ["Пуск!", "Атакую!", "Захват!", "Цель вижу!"],
        "cr": ["Су тридцать пять готов."]}),
    "DroneOrlan": ("orl", "veh", "a reconnaissance drone operator, calm and observant", {
        "se": ["Орлан.", "Наблюдаю.", "Слушаю.", "Картинка есть."],
        "mo": ["Перемещаюсь.", "Есть.", "Принял.", "Следую."],
        "at": ["Цель вижу.", "Наводка есть.", "Передаю координаты.", "Корректирую."],
        "cr": ["Орлан в воздухе."]}),
    "HeliKa52": ("k52", "air", "an attack helicopter pilot in his thirties, through a helmet microphone, aggressive and controlled", {
        "se": ["Аллигатор.", "Слушаю.", "Готов.", "Борт в эфире."],
        "mo": ["Понял.", "Есть.", "Следую.", "Выполняю."],
        "at": ["Атакую!", "Пуск!", "Цель вижу!", "Работаю!"],
        "cr": ["Аллигатор готов."]}),
    "HeliMi8": ("mi8", "air", "a transport helicopter pilot in his forties, through a helmet microphone, calm and reliable", {
        "se": ["Ми восемь.", "Слушаю.", "Борт готов.", "Борт в эфире."],
        "mo": ["Понял.", "Есть.", "Следую.", "Выполняю."],
        "at": ["Работаю.", "Огонь!", "Высаживаю.", "Есть."],
        "cr": ["Ми восемь готов."]}),
}


# диктор: событие Eva -> (код файла, реплика); набор событий тот же, что у Китая (36 с репликой)
EVA = {
    "LowPower": ("power", "Внимание. Недостаточно электроэнергии."),
    "InsufficientFunds": ("funds", "Недостаточно средств."),
    "SuperweaponDetected_Enemy_ParticleCannon": ("depar", "Обнаружена вражеская орбитальная пушка."),
    "SuperweaponDetected_Enemy_Nuke": ("denuk", "Обнаружена вражеская ядерная ракета."),
    "SuperweaponDetected_Enemy_ScudStorm": ("descu", "Обнаружен вражеский ракетный комплекс Скад."),
    "SuperweaponLaunched_Own_ParticleCannon": ("opar", "Орбитальный удар нанесён."),
    "SuperweaponLaunched_Own_Nuke": ("onuk", "Орешник, пуск произведён."),
    "SuperweaponLaunched_Own_ScudStorm": ("oscu", "Ракетный удар нанесён."),
    "SuperweaponLaunched_Ally_ParticleCannon": ("apar", "Союзник нанёс орбитальный удар."),
    "SuperweaponLaunched_Ally_Nuke": ("anuk", "Союзник запустил ядерную ракету."),
    "SuperweaponLaunched_Ally_ScudStorm": ("ascu", "Союзник нанёс ракетный удар."),
    "SuperweaponLaunched_Enemy_ParticleCannon": ("lpar", "Внимание! Противник нанёс орбитальный удар."),
    "SuperweaponLaunched_Enemy_Nuke": ("lnuk", "Внимание! Противник запустил ядерную ракету."),
    "SuperweaponLaunched_Enemy_ScudStorm": ("lscu", "Внимание! Противник нанёс ракетный удар."),
    "SuperweaponReady_Own_ParticleCannon": ("rpar", "Орбитальная пушка готова."),
    "SuperweaponReady_Own_Nuke": ("rnuk", "Комплекс Орешник готов к пуску."),
    "SuperweaponReady_Own_ScudStorm": ("rscu", "Ракетный комплекс готов к удару."),
    "BaseUnderAttack": ("base", "Наша база атакована."),
    "AllyUnderAttack": ("ally", "Союзник атакован."),
    "BeaconDetected": ("beac", "Обнаружен сигнальный маяк."),
    "EnemyBlackLotusDetected": ("eblo", "Обнаружен вражеский хакер Чёрный Лотос."),
    "EnemyJarmenKellDetected": ("ejar", "Обнаружен вражеский снайпер Джармен Келл."),
    "EnemyColonelBurtonDetected": ("ebur", "Обнаружен вражеский спецназовец полковник Бертон."),
    "OwnBlackLotusDetected": ("oblo", "Спецназ ГРУ прибыл."),
    "OwnJarmenKellDetected": ("ojar", "Наш снайпер на позиции."),
    "OwnColonelBurtonDetected": ("obur", "Наш спецназ на позиции."),
    "UnitLost": ("lost", "Мы потеряли подразделение."),
    "GeneralLevelUp": ("promo", "Получено новое звание. Доступны новые возможности."),
    "VehicleStolen": ("vsto", "Наша техника захвачена противником."),
    "BuildingStolen": ("bsto", "Наше здание захвачено противником."),
    "BuildingBeingStolen": ("bcap", "Противник захватывает наше здание."),
    "BuildingSabotaged": ("sabo", "Диверсия на нашей базе."),
    "CashStolen": ("cash", "Противник похитил наши средства."),
    "UpgradeComplete": ("upgr", "Модернизация завершена."),
    "SuperweaponLaunched_Enemy_Sneak_Attack": ("snea", "Внимание! Противник прорывается из туннелей."),
    "SuperweaponLaunched_Enemy_GPS_Scrambler": ("gps", "Противник глушит спутниковую навигацию."),
}

EVA_VOICE = ("Calm, clear female voice of a professional Russian military operations officer reading "
             "announcements over a command radio. Composed, precise, authoritative, slightly stern.")
EVA_REF = "Внимание. Говорит штаб. Обстановка под контролем, ждём ваших распоряжений."
EVA_FX = "highpass=f=200,lowpass=f=5000,acompressor=threshold=-20dB:ratio=3"


def norm(t):
    return re.sub(r"[^а-яё ]", "", t.lower().replace("ё", "е")).split()


def sim(a, b):
    return difflib.SequenceMatcher(None, " ".join(norm(a)), " ".join(norm(b))).ratio()


def post(raw, out, fx, dur):
    """обработка окружения + громкость как у EA, 22050 моно 16 бит"""
    tail = ["-ac", "1", "-ar", "22050", "-sample_fmt", "s16", out]
    norm_ = "loudnorm=I=-16:TP=-1.5:LRA=7,aresample=22050"
    if fx == "TANK":
        cmd = ["-i", raw, "-f", "lavfi", "-i", "anoisesrc=c=brown:a=0.35:d=%.2f" % (dur + 0.6),
               "-filter_complex", TANK + "," + norm_]
    else:
        cmd = ["-i", raw, "-af", fx + "," + norm_]
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y"] + cmd + tail, check=True)


def vanilla_sounds(vanilla, src):
    txt = ""
    for f in glob.glob(os.path.join(vanilla, "Data", "INI", "Object", "*.ini")):
        txt += open(f, encoding="latin-1").read().replace("\r", "") + "\n"
    m = re.search(r"^Object " + re.escape(src) + r"\s*\n(.*?)^End", txt, re.S | re.M)
    assert m, src
    body = m.group(1)
    u = re.search(r"\n\s*UnitSpecificSounds\s*\n(.*?)\n\s*End", body, re.S)
    us = re.findall(r"^\s*(\w+)\s*=\s*(\S+)", u.group(1), re.M) if u else []
    main = re.findall(r"^\s*(Voice\w+)\s*=\s*(\S+)", body.replace(u.group(0), "") if u else body, re.M)
    return main, us


def slot(key, has_fear):
    if "Create" in key:
        return "Create"
    if "Fear" in key:
        return "Fear" if has_fear else "Select"
    if "Select" in key:
        return "Select"
    if any(w in key for w in ("Attack", "RapidFire", "Bombard", "FireRocketPods", "Melee", "Subdue", "Crush", "Clear")):
        return "Attack"
    return "Move"


def splice(path, block):
    s = open(path, encoding="utf-8").read()
    if BEGIN in s:
        a, rest = s.split(BEGIN, 1)
        s = a + BEGIN + block + END + rest.split(END, 1)[1]
    else:
        s = s.rstrip("\n") + "\n\n" + BEGIN + block + END
    open(path, "w", encoding="utf-8", newline="\n").write(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vanilla", required=True, help="распакованный INIZH.big (папка с Data/INI/Object)")
    ap.add_argument("--asr", default="medium")
    ap.add_argument("--only")
    ap.add_argument("--what", default="all", choices=["units", "eva", "all"])
    ap.add_argument("--ini-only", action="store_true", help="не синтезировать, только INI")
    args = ap.parse_args()
    gen = open(os.path.join(HERE, "gen.py"), encoding="utf-8").read()
    src = dict(re.findall(r'\("([A-Za-z0-9]+)", "([A-Za-z_]+)", \d+', gen))
    if not args.ini_only:
        import numpy as np
        import soundfile as sf
        from mlx_audio.tts.utils import load_model
        tts = load_model(MODEL)
        asr = None
        if args.asr != "none":
            from faster_whisper import WhisperModel
            asr = WhisperModel(args.asr, compute_type="int8")
        tmp = tempfile.mkdtemp()
        worst = []

        def make(text, instruct, ref=None):
            """лучший из TRIES синтезов по сходству распознанного текста; ref - (wav, текст) для клонирования"""
            best = (-1, None, "")
            for _ in range(TRIES):
                if ref:
                    gen = clone.generate(text=text, ref_audio=ref[0], ref_text=ref[1], lang_code="russian")
                else:
                    gen = tts.generate(text=text, instruct=instruct, lang_code="russian")
                a = np.concatenate([np.array(r.audio) for r in gen])
                if asr is None:
                    return (1.0, a, "")
                x = np.interp(np.arange(0, len(a), tts.sample_rate / 16000), np.arange(len(a)), a).astype(np.float32)
                heard = " ".join(s.text for s in asr.transcribe(x, language="ru")[0])
                r = sim(text, heard)
                if r > best[0]:
                    best = (r, a, heard)
                if r >= MIN_SIM:
                    break
            return best

        jobs = []
        if args.what in ("units", "all"):
            for obj, (code, cls, who, lines) in U.items():
                desc, fx, _ = CLS[cls]
                for kind, texts in lines.items():
                    for n, text in enumerate(texts):
                        jobs.append((code, "r%s%s%s" % (code, kind, "abcdefgh"[n]), text, "Sounds",
                                     desc.format(who), fx))
        refs = {}
        clone = load_model(CLONE)

        def unit_ref(code, desc):
            """эталон голоса юнита: VoiceDesign один раз на юнит"""
            if code not in refs:
                r, a, heard = make(UNIT_REF, desc + " " + UNIT_REF_MOOD)
                print("%s ref %.2f | %s" % (code, r, heard.strip()), flush=True)
                refs[code] = (os.path.join(tmp, code + "_ref.wav"), UNIT_REF)
                sf.write(refs[code][0], a, tts.sample_rate)
            return refs[code]

        eva_ref = None
        if args.what in ("eva", "all"):
            # эталон диктора: голос по описанию один раз, дальше все реплики клонируются с него
            r, a, heard = make(EVA_REF, EVA_VOICE)
            print("eva ref %.2f | %s" % (r, heard.strip()), flush=True)
            eva_ref = (os.path.join(tmp, "eva_ref.wav"), EVA_REF)
            sf.write(eva_ref[0], a, tts.sample_rate)
            for ev_name, (code, text) in EVA.items():
                jobs.append((code, "er" + code, text, "Speech", EVA_VOICE, EVA_FX))
        for code, name, text, folder, instruct, fx in jobs:
            if args.only and code != args.only:
                continue
            r, a, heard = make(text, instruct, eva_ref if folder == "Speech" else unit_ref(code, instruct))
            raw = os.path.join(tmp, "raw.wav")
            sf.write(raw, a, tts.sample_rate)
            post(raw, os.path.join(D, "Audio", folder, name + ".wav"), fx, len(a) / tts.sample_rate)
            print("%s %.2f %s | %s" % (name, r, text, heard.strip()), flush=True)
            if r < MIN_SIM:
                worst.append(name)
        print("below %.2f: %d %s" % (MIN_SIM, len(worst), " ".join(worst)))
    # INI
    ev, objs = [], []
    for obj, (code, cls, who, lines) in U.items():
        radio = CLS[cls][2]
        name = "Russia" + obj
        for kind, texts in lines.items():
            k = KINDS[kind]
            ev.append("AudioEvent %sVoice%s" % (name, k))
            ev.append("  Sounds = " + " ".join("r%s%s%s" % (code, kind, "abcdefgh"[n]) for n in range(len(texts))))
            if radio and kind != "cr":
                ev += ["  Attack = gradio1a gradio1b gradio1c gradio1d gradio1e gradio1f",
                       "  Decay = gradio3a gradio3b gradio3c gradio3d gradio3e"]
            ev.append("  Control = random")
            ev += {"cr": ["  Volume = 110", "  MinVolume = 100", "  Priority = high", "  Type = world global player"],
                   "fe": ["  Volume = 100", "  MinVolume = 90", "  Type = world shrouded player"]}.get(
                kind, ["  Volume = 90", "  Type = ui voice player"])
            ev += ["End", ""]
        main, us = vanilla_sounds(args.vanilla, src[obj])
        fear = "fe" in lines
        o = ["Object " + name]
        for key, _ in main:
            s = slot(key, fear)
            if s:
                o.append("  %s = %sVoice%s" % (key, name, s))
        o.append("  UnitSpecificSounds")
        for key, val in us:
            s = slot(key, fear) if key.startswith("Voice") else None
            o.append("    %s = %s" % (key, "%sVoice%s" % (name, s) if s else val))
        o += ["  End", "End", ""]
        objs.append("\n".join(o))
    for ev_name, (code, text) in EVA.items():
        ev += ["DialogEvent EvaRussia_" + ev_name, "  Filename = er%s.wav" % code, "End", ""]
    splice(os.path.join(D, "INI", "VoiceReforged.ini"),
           "; Russia's unit voices and announcer: Qwen3-TTS VoiceDesign (Apache-2.0), Tools/Russia/voices.py.\n"
           "; Unit wavs Code/Data/Audio/Sounds/r<code><kind><n>.wav, announcer Code/Data/Audio/Speech/er<code>.wav.\n\n"
           + "\n".join(ev))
    eva = ["; Russia's announcer, one line per event China speaks (Tools/Russia/voices.py)", ""]
    for ev_name in EVA:
        eva += ["EvaEvent " + ev_name, "  SideSounds", "    Side = Russia", "    Sounds = EvaRussia_" + ev_name, "  End", "End", ""]
    splice(os.path.join(D, "INI", "EvaReforged.ini"), "\n".join(eva))
    splice(os.path.join(D, "INI", "RussiaReforged.ini"), "\n".join(objs))
    print("ini ok:", len(U), "units")


if __name__ == "__main__":
    main()
