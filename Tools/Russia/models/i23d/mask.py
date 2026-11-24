import sys, numpy as np, cv2
from PIL import Image
im=np.array(Image.open(sys.argv[1]).convert('RGB'))
h,w,_=im.shape
mask=np.zeros((h+2,w+2),np.uint8)
ff=im.copy()
for p in [(0,0),(w-1,0),(0,h-1),(w-1,h-1)]:
    cv2.floodFill(ff,mask,p,(0,0,0),(6,6,6),(6,6,6),cv2.FLOODFILL_FIXED_RANGE|cv2.FLOODFILL_MASK_ONLY|(255<<8))
bg=mask[1:-1,1:-1]>0
a=np.where(bg,0,255).astype(np.uint8)
a=cv2.morphologyEx(a,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
Image.fromarray(np.dstack([im,a])).save(sys.argv[2])
print('fg frac',(a>0).mean())
