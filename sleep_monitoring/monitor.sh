#!/bin/bash

echo "Memulai monitoring... Log akan dicatat setiap 30 detik."

# Menambahkan timestamp saat monitoring pertama kali dimulai
echo "--- $(date) ---" >> system_stats.log

# Jalankan tegrastats dengan interval 30 detik (30000 milidetik)
# dan arahkan semua outputnya ke file log.
# tegrastats akan berjalan terus-menerus hingga dihentikan (Ctrl+C).
tegrastats --interval 30000 >> system_stats.log