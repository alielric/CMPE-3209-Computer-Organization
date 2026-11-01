/* Ali Paşaoğlu 5001230022, G3 Mesaj sifreleme ve butunluk */
#define N 46                        /* N = 24 + (22 mod 25) */

int msg[N];                         /* mesaj dizisi ('A'-'Z') */
unsigned int checksum;              /* sonuc 1 */
int decrypt_ok;                     /* sonuc 2 */

unsigned int lcg_next(unsigned int x) {
    return 1664525u * x + 1013904223u;
}

unsigned int rotl1(unsigned int c) {
    return (c << 1) | (c >> 31);
}

int main(void) {
    const int SID = 1230022;        /* son 9 hane: 001230022 */
    int key = SID % 256;            /* K = 198 = 0xC6 */
    if (key == 0)
        key = 0xA5;
    unsigned int x = SID;
    int i;
    for (i = 0; i < N; i++) {       /* 1. gecis: girdi uret */
        x = lcg_next(x);
        msg[i] = (int)((x >> 16) % 26) + 65;
    }
    for (i = 0; i < N; i++)         /* 2. gecis: sifrele */
        msg[i] = msg[i] ^ key;
    unsigned int c = 0;
    for (i = 0; i < N; i++)         /* 3. gecis: checksum */
        c = rotl1(c) + (unsigned int)msg[i];
    checksum = c;
    for (i = 0; i < N; i++)         /* 4. gecis: sifreyi coz */
        msg[i] = msg[i] ^ key;
    x = SID;                        /* ureteci bastan calistir */
    decrypt_ok = 1;
    for (i = 0; i < N; i++) {       /* 5. gecis: orijinalle karsilastir */
        x = lcg_next(x);
        if (msg[i] != (int)((x >> 16) % 26) + 65)
            decrypt_ok = 0;
    }
    return 0;
}
