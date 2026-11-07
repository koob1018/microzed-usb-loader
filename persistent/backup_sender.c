typedef unsigned int u32;
typedef unsigned char u8;
#define R(a) (*(volatile u32*)(a))
static void tx(u8 x){while(R(0xe000102c)&0x10){} R(0xe0001030)=x;}
static int rx(void){for(u32 n=0;n<500000000;n++){if(!(R(0xe000102c)&2))return R(0xe0001030)&255;}return -1;}
static void str(const char*s){while(*s)tx(*s++);}
static void word(u32 x){for(int i=0;i<4;i++){tx(x&255);x>>=8;}}
static u32 crc(const u8*p,u32 n){u32 c=~0u;while(n--){c^=*p++;for(int i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1));}return ~c;}
static void speed(u32 gen,u32 div){while((R(0xe000102c)&0x808)!=8){} R(0xe0001000)=0x128;R(0xe0001018)=gen;R(0xe0001034)=div;R(0xe0001000)=0x103;R(0xe0001000)=0x114;__asm__ volatile("dsb sy":::"memory");}
__attribute__((section(".text.entry"))) int entry(int argc,char**argv){
 u32 total=0x1000000,gen=R(0xe0001018),div=R(0xe0001034);int rc=0;
 if(argc>1){total=0;const char*p=argv[1];while(*p){char c=*p++;u32 d=c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:99;if(d>15)return 5;total=total*16+d;}}
 if(!total||total>0x1000000)return 6;
 str("\r\nMZ_BACKUP_READY\r\n");if(rx()!='H')return 2;
 speed(6,8);if(rx()!='R'){rc=3;goto done;}
 for(u32 off=0;off<total;){u32 n=total-off;if(n>0x10000)n=0x10000;const u8*p=(const u8*)(0x08000000+off);u32 c=crc(p,n);int ack;
  do{str("MZBK");word(off);word(n);word(c);for(u32 i=0;i<n;i++)tx(p[i]);ack=rx();}while(ack=='N');
  if(ack!='A'){rc=4;goto done;}off+=n;
 }
 done:speed(gen,div);return rc;
}
