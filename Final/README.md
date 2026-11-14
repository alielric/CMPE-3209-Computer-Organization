# CMPE3209 — Final paketi (Ali Paşaoğlu, 5001230022, G3)

| Dosya | Açıklama |
|---|---|
| CMPE3209_Proje_Teslim_Tutanagi.docx / .pdf | Tüm adımları (0–5) dolu tutanak |
| main.c | Program (SID = 706262726 = 5001230022'nin alt 32 biti) |
| main_v2.c | 4g sürümü: main'e `int pad[36];` eklendi (stack 144 B kayar) |
| asm_O0.txt, asm_O1.txt, asm_v2_O0.txt | Ripes v2.3.1 disassembly listeleri (objdump -d karşılığı) |
| objdump_O0.txt, objdump_O1.txt, objdump_v2_O0.txt | GCC 8.3.0 ile derlenen ELF'lerin `objdump -d` çıktısı; Ripes listeleriyle birebir aynı |
| main_v2_O0.elf | main_v2.c'nin ELF dosyası (riscv64-unknown-elf-gcc 8.3.0, -march=rv32im -mabi=ilp32 -O0); Aşama 2'nin main_O0.elf ve main_O1.elf dosyaları M2 klasöründe |
| asm_O0_eslesme.txt | -O0 listesi, her instruction'ın C satırıyla |
| rvsim.py | RV32IM komut simülatörü: listedeki makine kodunu _start'tan exit'e çalıştırır, data izini ve dinamik Ic'yi çıkarır |
| cachesim.py | Cache simülatörü: boyut / line / yol parametreli, LRU, write-back + write-allocate |
| trace.csv, trace_v2.csv | -O0 data adres izleri (main.c, main_v2.c) |
| sonuclar.txt | Simülatör çıktıları |
| cache_tasarim_uzayi.png | 4e grafiği |
| cache_ripes.png, cache_ripes_v2.png | Ripes data cache doğrulaması (2347/149/89 ve 2400/96/50) |
| ripes_icache_ic.png | Ripes cycle sayısı = 6478 (Ic doğrulaması) |

## Çalıştırma (Python 3)

    python3 rvsim.py asm_O0.txt              # Ic, sınıflar, referans sayısı
    python3 cachesim.py trace.csv 256 16 1   # boyut, line, way (1 = direct)
    python3 cachesim.py trace.csv 256 16 2   # 2-way
    python3 cachesim.py trace.csv 256 64 1   # 64 B line

Doğrulama: simülatör hem main.c hem main_v2.c için Ripes'in data cache istatistiklerini
(hit/miss/writeback) ve -O0 cycle sayısını birebir verir; program sonucu checksum = 0x255D2CDD,
decrypt_ok = 1.

Varsayım: Ripes'in ELF'ten yüklediği ilk veri değerlerinden yalnızca C kütüphanesinin kullandığı
üç tanesi simülatörde elle kuruldu (_global_impure_ptr, .init_array, .fini_array; bkz. rvsim.py).
Bunlar yalnızca başlangıç/bitiş kodunu etkiler; main'in izi bunlardan bağımsızdır.
