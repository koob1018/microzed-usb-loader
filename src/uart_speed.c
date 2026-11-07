typedef unsigned int u32;
#define R(a) (*(volatile u32*)(a))
static u32 gen,div;
/* Included in the binary: never restore uninitialized divisors. */
static volatile u32 ready=0x55415200;
__attribute__((section(".text.entry"))) int entry(int argc,char**argv){
 u32 g,d;
 if(argc>1 && argv[1][0]=='f'){
  if(ready!=0x55415201){gen=R(0xe0001018);div=R(0xe0001034);ready=0x55415201;}
  g=6;d=8;
 }
 else {if(ready!=0x55415201)return 0;g=gen;d=div;ready=0x55415200;}
 while((R(0xe000102c)&0x808)!=8){}
 R(0xe0001000)=0x128;R(0xe0001018)=g;R(0xe0001034)=d;
 R(0xe0001000)=0x103;R(0xe0001000)=0x114;
 __asm__ volatile("dsb sy":::"memory");return 0;
}
