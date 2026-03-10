$env:AURELM_DB_PATH = 'C:\Users\alexi\Documents\projects\Aurelm\pipeline\aurelm_t01t08_fresh.db'
Set-Location 'C:\Users\alexi\Documents\projects\Aurelm\gui'
flutter run -d windows --no-pub 2>&1 | Tee-Object -FilePath 'C:\Users\alexi\Documents\projects\Aurelm\flutter_debug.log'
