/*
**	Command & Conquer Generals Zero Hour(tm)
**	Copyright 2025 Electronic Arts Inc.
**
**	This program is free software: you can redistribute it and/or modify
**	it under the terms of the GNU General Public License as published by
**	the Free Software Foundation, either version 3 of the License, or
**	(at your option) any later version.
**
**	This program is distributed in the hope that it will be useful,
**	but WITHOUT ANY WARRANTY; without even the implied warranty of
**	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
**	GNU General Public License for more details.
**
**	You should have received a copy of the GNU General Public License
**	along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

////////////////////////////////////////////////////////////////////////////////
//																																						//
//  (c) 2001-2003 Electronic Arts Inc.																				//
//																																						//
////////////////////////////////////////////////////////////////////////////////

// FILE: CashHackSpecialPower.cpp /////////////////////////////////////////////////////////////
// Author: Amit Kumar, July 2002
// Desc:   The Cash Hack will steal money from an enemy player
///////////////////////////////////////////////////////////////////////////////////////////////////

// INCLUDES ///////////////////////////////////////////////////////////////////////////////////////
#include "PreRTS.h"	// This must go first in EVERY cpp file int the GameEngine

#include "Common/Player.h"
#include "Common/Team.h"
#include "Common/Xfer.h"
#include "GameClient/GameText.h"
#include "GameLogic/Object.h"
#include "GameLogic/ObjectCreationList.h"
#include "GameLogic/PartitionManager.h"
#include "GameLogic/Module/CashHackSpecialPower.h"
#include "GameClient/ControlBar.h"
#include "GameClient/InGameUI.h"

// ------------------------------------------------------------------------------------------------
// ------------------------------------------------------------------------------------------------
CashHackSpecialPowerModuleData::CashHackSpecialPowerModuleData( void )
{
	m_upgrades.clear();
	m_defaultAmountToSteal = 0;
	m_upgradeOCL.clear();
	m_defaultOCL = NULL;
}

//-------------------------------------------------------------------------------------------------
//-------------------------------------------------------------------------------------------------
static void parseCashHackUpgradePair( INI* ini, void * /*instance*/, void *store, const void* /*userData*/ )
{
	CashHackSpecialPowerModuleData::Upgrades up;

	INI::parseScience(ini, NULL, &up.m_science, NULL);
	INI::parseInt(ini, NULL, &up.m_amountToSteal, NULL);

	std::vector<CashHackSpecialPowerModuleData::Upgrades>* s = (std::vector<CashHackSpecialPowerModuleData::Upgrades>*)store;
	s->push_back(up);
} 

// ------------------------------------------------------------------------------------------------
// ------------------------------------------------------------------------------------------------
static void parseCashHackOCLPair( INI* ini, void * /*instance*/, void *store, const void* /*userData*/ )
{
	CashHackSpecialPowerModuleData::OCLUpgrade up;

	INI::parseScience(ini, NULL, &up.m_science, NULL);
	INI::parseObjectCreationList(ini, NULL, &up.m_ocl, NULL);

	std::vector<CashHackSpecialPowerModuleData::OCLUpgrade>* s = (std::vector<CashHackSpecialPowerModuleData::OCLUpgrade>*)store;
	s->push_back(up);
}

/*static*/ void CashHackSpecialPowerModuleData::buildFieldParse(MultiIniFieldParse& p)
{
	SpecialPowerModuleData::buildFieldParse( p );
	
	static const FieldParse dataFieldParse[] = 
	{
		{ "UpgradeMoneyAmount", parseCashHackUpgradePair, NULL, offsetof( CashHackSpecialPowerModuleData, m_upgrades ) },
		{ "MoneyAmount", INI::parseInt, NULL, offsetof( CashHackSpecialPowerModuleData, m_defaultAmountToSteal ) },
		{ "UpgradeOCL", parseCashHackOCLPair, NULL, offsetof( CashHackSpecialPowerModuleData, m_upgradeOCL ) },
		{ "OCL", INI::parseObjectCreationList, NULL, offsetof( CashHackSpecialPowerModuleData, m_defaultOCL ) },
		{ 0, 0, 0, 0 }
	};
	p.add(dataFieldParse);
	
}  // end buildFieldParse

///////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////////////////////////

// ------------------------------------------------------------------------------------------------
// ------------------------------------------------------------------------------------------------
CashHackSpecialPower::CashHackSpecialPower( Thing *thing, const ModuleData *moduleData )
												: SpecialPowerModule( thing, moduleData )
{

}  // end CashHackSpecialPower

// ------------------------------------------------------------------------------------------------
// ------------------------------------------------------------------------------------------------
CashHackSpecialPower::~CashHackSpecialPower( void )
{

}  // end ~CashHackSpecialPower

// ------------------------------------------------------------------------------------------------
// ------------------------------------------------------------------------------------------------
void CashHackSpecialPower::doSpecialPowerAtLocation( const Coord3D *loc, Real angle, UnsignedInt commandOptions )
{
	if (getObject()->isDisabled())
		return;

	// A player can only aim it at an object.  The AI's fire-when-ready aims at a spot
	// (AIPlayer::doReadySpecialPowers): hack the enemy building nearest to it, or nothing.
	if ((commandOptions & COMMAND_FIRED_BY_SCRIPT) == 0 || loc == NULL)
		return;
	PartitionFilterRelationship enemies(getObject(), PartitionFilterRelationship::ALLOW_ENEMIES);
	PartitionFilterAcceptByKindOf structures(MAKE_KINDOF_MASK(KINDOF_STRUCTURE), KINDOFMASK_NONE);
	PartitionFilterSameMapStatus mapStatus(getObject());
	PartitionFilter *filters[] = { &enemies, &structures, &mapStatus, NULL };
	Object *victim = ThePartitionManager->getClosestObject(loc, 300.0f, FROM_CENTER_2D, filters);
	if (victim != NULL)
		doSpecialPowerAtObject(victim, commandOptions);
}  

//-------------------------------------------------------------------------------------------------
//-------------------------------------------------------------------------------------------------
Int CashHackSpecialPower::findAmountToSteal() const
{
	const CashHackSpecialPowerModuleData* d = getCashHackSpecialPowerModuleData();
	const Player* controller = getObject()->getControllingPlayer();
	if (controller != NULL)
	{
		for (std::vector<CashHackSpecialPowerModuleData::Upgrades>::const_iterator it = d->m_upgrades.begin(); 
					it != d->m_upgrades.end();
					++it)
		{
			if (controller->hasScience(it->m_science))
				return it->m_amountToSteal;
		}
	}
	return d->m_defaultAmountToSteal;
}

// ------------------------------------------------------------------------------------------------
// ------------------------------------------------------------------------------------------------
const ObjectCreationList* CashHackSpecialPower::findOCL() const
{
	const CashHackSpecialPowerModuleData* d = getCashHackSpecialPowerModuleData();
	const Player* controller = getObject()->getControllingPlayer();
	if (controller != NULL)
	{
		for (std::vector<CashHackSpecialPowerModuleData::OCLUpgrade>::const_iterator it = d->m_upgradeOCL.begin();
					it != d->m_upgradeOCL.end();
					++it)
		{
			if (controller->hasScience(it->m_science))
				return it->m_ocl;
		}
	}
	return d->m_defaultOCL;
}

void CashHackSpecialPower::doSpecialPowerAtObject( Object *victim, UnsignedInt commandOptions )
{
	if (getObject()->isDisabled())
		return;

	// sanity
	if (!victim)
		return;

	// call the base class action cause we are *EXTENDING* functionality
  SpecialPowerModule::doSpecialPowerAtObject( victim, commandOptions );

	// get our module data
	Object *self = getObject();

	//Steal a thousand cash from the other team!
	Money *targetMoney = victim->getControllingPlayer()->getMoney();
	Money *selfMoney = self->getControllingPlayer()->getMoney();
	if( targetMoney && selfMoney )
	{
		UnsignedInt cash = targetMoney->countMoney();
		UnsignedInt desiredAmount = findAmountToSteal();
		//Check to see if they have 1000 cash, otherwise, take the remainder!
		cash = min( desiredAmount, cash );
		if( cash > 0 )
		{
			//Steal the cash
			targetMoney->withdraw( cash );
			const UnsignedInt earned = self->getControllingPlayer()->earnMoney( cash );

			//Display cash income floating over the blacklotus
			Coord3D pos;
			pos.set( self->getPosition() );
			pos.z += 20.0f; //add a little z to make it show up above the unit.
			TheInGameUI->addMoneyText( (Int)earned, &pos, self->getControllingPlayer() );

			//Display cash lost floating over the target
			pos.set( victim->getPosition() );
			pos.z += 30.0f; //add a little z to make it show up above the unit.
			TheInGameUI->addMoneyText( -(Int)cash, &pos, victim->getControllingPlayer() );
		}
	}

	const ObjectCreationList *ocl = findOCL();
	if( ocl )
		ObjectCreationList::create( ocl, self, victim->getPosition(), victim->getPosition(), 0.0f );

}  

// ------------------------------------------------------------------------------------------------
/** CRC */
// ------------------------------------------------------------------------------------------------
void CashHackSpecialPower::crc( Xfer *xfer )
{

	// extend base class
	SpecialPowerModule::crc( xfer );

}  // end crc

// ------------------------------------------------------------------------------------------------
/** Xfer method
	* Version Info:
	* 1: Initial version */
// ------------------------------------------------------------------------------------------------
void CashHackSpecialPower::xfer( Xfer *xfer )
{

	// version
	XferVersion currentVersion = 1;
	XferVersion version = currentVersion;
	xfer->xferVersion( &version, currentVersion );

	// extend base class
	SpecialPowerModule::xfer( xfer );

}  // end xfer

// ------------------------------------------------------------------------------------------------
/** Load post process */
// ------------------------------------------------------------------------------------------------
void CashHackSpecialPower::loadPostProcess( void )
{

	// extend base class
	SpecialPowerModule::loadPostProcess();

}  // end loadPostProcess
