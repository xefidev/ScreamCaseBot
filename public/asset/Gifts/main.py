import os
import requests

# Идеальные ссылки, которые ты нашёл
REAL_URLS = {
    "B-day Candle": ("500S_B_day_Candle_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/B-Day%20Candle.webp"),
    "Chill Flame": ("50S_Chill_Flame_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Torch%20of%20Freedom.webp"),
    "Durov's Boots": ("41000S_Durovs_Boots_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Durovs%20Boots.webp"),
    "Durov's Cap": ("72792S_Durovs_Cap_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Durovs%20Cap.webp"),
    "Durov's Coat": ("10000S_Durovs_Coat_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Durovs%20Coat.webp"),
    "Durov's Figurine": ("10000S_Durovs_Figurine_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Durovs%20Figurine.webp"),
    "Khabib's Papakha": ("34S_Khabibs_Papakha_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Khabibs%20Papakha.webp"),
    "Mood Pack": ("3S_Mood_Pack_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Backpack.webp"),
    "New Year's Bear": ("355S_New_Years_Bear_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Bear%20New%20Year.webp"),
    "Pool Float": ("243S_Pool_Float_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Pink%20Flamingo.webp"),
    "Rare Bird": ("7S_Rare_Bird_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Plane.webp"),
    "Timeless Book": ("570S_Timeless_Book_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Book.webp"),
    "Vice Cream": ("2S_Vice_Cream_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Ice%20Cream%20Cone.webp"),
    "Victory Medal": ("23S_Victory_Medal_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Medal.webp"),
    "Telegram Pin": ("2S_Telegram_Pin_Original.webp", "https://telegifter.ru/wp-content/themes/gifts/assets/img/gifts/noupdate/Crystal%20Eagle.webp")
}

def run_final_fix():
    main_dir = "Scream_Gifts_Perfect"
    os.makedirs(main_dir, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print("[+] Начинаем финальный засыл по твоим секретным ссылкам...\n")
    
    for original_name, (file_name, url) in REAL_URLS.items():
        # Формируем красивое имя папки без мусора
        folder_name = file_name.split('S_')[1].replace('_Original.webp', '')
        gift_folder_path = os.path.join(main_dir, folder_name)
        os.makedirs(gift_folder_path, exist_ok=True)
        
        save_path = os.path.join(gift_folder_path, file_name)
        
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(res.content)
                print(f"[+] УСПЕШНО ДОБИТ: {file_name}")
            else:
                if not os.listdir(gift_folder_path):
                    os.rmdir(gift_folder_path)
                print(f"[!] Чёрт, сервер ответил {res.status_code} на: {url}")
        except Exception as e:
            if not os.listdir(gift_folder_path):
                os.rmdir(gift_folder_path)
            print(f"[!] Ошибка сети для {original_name}: {e}")

if __name__ == "__main__":
    run_final_fix()