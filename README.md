# PRE TOU (Time of Use) Distribuce pro Home Assistant
## CZ

> [!IMPORTANT]  
> Tato integrace bylaz z 99% vytovřena pomocí AI pro mé vlastní užití a není garantována funkčnost, kvalita ani bezpečnost kódu. 

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B%20%7C%202026.9%2B-blue.svg)](https://www.home-assistant.io/)

Integrace pro **Home Assistant** (kompatibilní s **HACS** a verzemi **2026.9 a novějšími**), která počítá aktuální stav vysokého tarifu (**VT**) a nízkého tarifu (**NT**) i časy jejich dalšího spuštění na základě oficiálních **TOU (Time of Use)** tabulek **PREdistribuce, a. s.**

Nové typy chytrých elektroměrů v síti PRE (např. *Landis+Gyr*, *ZPA AM175 / AM375*, *NP71E*, *CLMS*, *AD11A*) nepoužívají dynamické rádiové pulzy HDO, ale mají časy spínání uloženy přímo v paměti elektroměru v tzv. **TOU tabulce**. Kód vašeho programu (např. `TD25_001`, `TD57_001`) svítí přímo na displeji elektroměru.

---

## ⚡ Vytvářené entity

Integrace po přidání do Home Assistant automaticky vytvoří zařízení a sadu entit:

| Entita | Typ | Popis |
|---|---|---|
| `binary_sensor.<id>_vt` | `binary_sensor` | **Vysoký tarif (VT)** – `on` když právě běží VT, `off` když běží NT |
| `binary_sensor.<id>_nt` | `binary_sensor` | **Nízký tarif (NT)** – `on` když právě běží NT, `off` když běží VT |
| `sensor.<id>_next_vt` | `sensor` (timestamp) | **Čas příštího spuštění VT** (`device_class: timestamp`) |
| `sensor.<id>_next_nt` | `sensor` (timestamp) | **Čas příštího spuštění NT** (`device_class: timestamp`) |
| `sensor.<id>_current_tariff` | `sensor` | **Aktuální tarif** (`VT` / `NT`), v atributech obsahuje detailní časová okna pro dnešek i zítřek |
| `binary_sensor.<id>_rele_1` *(volitelné)* | `binary_sensor` | Stav spínacího relé 1 (např. bojler) |
| `sensor.<id>_next_rele_1` *(volitelné)* | `sensor` (timestamp) | Čas příštího sepnutí relé 1 |
| `binary_sensor.<id>_rele_2` *(volitelné)* | `binary_sensor` | Stav spínacího relé 2 (např. akumulace / přímotop, zohledňuje 1F/3F) |
| `sensor.<id>_next_rele_2` *(volitelné)* | `sensor` (timestamp) | Čas příštího sepnutí relé 2 |

### 📋 Atributy senzoru tarifu
Senzor `sensor.<id>_current_tariff` poskytuje doplňující atributy:
- `today_intervals`: Seznam všech časových pásem NT pro dnešní den `[{"start": "01:00:00", "end": "06:00:00"}, ...]`
- `tomorrow_intervals`: Seznam všech časových pásem NT pro zítřejší den
- `is_holiday`: Indikátor státního svátku v ČR (`true` / `false`)
- `day_type`: Typ dne podle PRE rozvrhu (`Pondělí - Čtvrtek`, `Pátek`, `Sobota`, `Neděle`, `Svátek`)
- `pre_name`: Oficiální kód povelu PRE (např. `TOU 503 504 504`)
- `tariff_register`, `rele1_register`, `rele2_register`: Kódy interních registrů elektroměru
- `phase`: Zvolené fázové zapojení (`3F` nebo `1F`)

---

## 🚀 Instalace

### Metoda 1: Přes HACS (Doporučeno)

1. V Home Assistant otevřete **HACS** -> **Integrace**.
2. V pravém horním rohu klikněte na tři tečky `⋮` -> **Vlastní repozitáře** (*Custom repositories*).
3. Vložte URL adresu tohoto repozitáře a jako kategorii zvolte **Integrace** (*Integration*).
4. Klikněte na **Přidat** (*Add*) a poté integraci vyhledejte a stáhněte.
5. **Restartujte Home Assistant**.

### Metoda 2: Manuální instalace

1. Stáhněte složku `custom_components/pre_tou` z tohoto repozitáře.
2. Nahrajte složku `pre_tou` do vašeho adresáře Home Assistant: `<config>/custom_components/pre_tou/`.
3. **Restartujte Home Assistant**.

---

## ⚙️ Nastavení (Config Flow)

1. V Home Assistant přejděte do **Nastavení** -> **Zařízení a služby** -> **Přidat integraci**.
2. Vyhledejte **PRE TOU Distribuce**.
3. V průvodci nastavením:
   - **Kód TOU**: Vyberte svůj kód z rozbalovacího seznamu (např. `TD25_001`, `TD57_001`, `TD26_002` atd.) nebo napište vlastní.
   - **Fázové zapojení**: Zvolte `Třífázový (3F)` nebo `Jednofázový (1F)` (u 1F se automaticky zohlední vynechání relé 2 podle tabulky PRE).
   - **Entity pro relé**: Zaškrtněte, pokud chcete vytvořit entity i pro spotřebičová relé 1 a 2.
   - **Vlastní CSV tabulka (volitelné)**: Pokud PRE v budoucnu vydá aktualizovanou tabulku nebo máte nestandardní tarif, můžete sem celou tabulku přímo vložit. Pokud pole necháte prázdné, použije se vestavěná oficiální databáze PRE.
4. Klikněte na **Odeslat**.

### Úprava nastavení (Options Flow)
Kdykoliv můžete kliknout na **Konfigurovat** u integrovaného zařízení a změnit TOU kód, fáze nebo vložit aktualizovanou CSV tabulku bez nutnosti integraci mazat.

---

## 🇨🇿 Podpora českých státních svátků a víkendů

Integrace plně respektuje specifika PREdistribuce:
- **Pátek, Sobota, Neděle**: Správné zohlednění odlišných časů o víkendech.
- **D61d (Víkendový tarif)**: Speciální režim od pátku 12:00 do neděle 22:00 (nepřetržitých 58 hodin NT).
- **Státní svátky (Sv)**: Automatický vestavěný kalendář všech pevných českých státních svátků i pohyblivých Velikonoc (Velký pátek i Velikonoční pondělí) – ve svátek se automaticky aktivuje sváteční rozvrh PRE.
- **Plynulý přechod přes půlnoc**: Žádné falešné přepínání na přelomu dní.

---

## 💡 Příklady automatizací

### 1. Spuštění ohřevu vody (bojleru) při přechodu do NT
```yaml
alias: "Bojler: Sepnout v NT"
trigger:
  - platform: state
    entity_id: binary_sensor.pre_tou_td25_001_nt_active
    to: "on"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.bojler
```

### 2. Upozornění na telefon 15 minut před začátkem drahého VT
```yaml
alias: "Upozornění: Blíží se vysoký tarif"
trigger:
  - platform: time
    at: sensor.pre_tou_td25_001_next_vt
    offset: "-00:15:00"
action:
  - service: notify.notify
    data:
      title: "⚡ Pozor, brzy začne vysoký tarif"
      message: "Za 15 minut skončí nízký tarif a začne VT. Dokončete energeticky náročné spotřebiče."
```

### 3. Zobrazení v Lovelace kartě
```yaml
type: entities
title: ⚡ PRE Distribuce – HDO & TOU
entities:
  - entity: sensor.pre_tou_td25_001_current_tariff
    name: Aktuální tarif
  - entity: binary_sensor.pre_tou_td25_001_nt_active
    name: Nízký tarif (NT)
  - entity: sensor.pre_tou_td25_001_next_nt
    name: Příští začátek NT
  - entity: sensor.pre_tou_td25_001_next_vt
    name: Příští začátek VT
```

---

## 🛠️ Podporované sazby v databázi

Vestavěná databáze obsahuje kompletní oficiální tabulku PRE `TOU_tabulka-T.xlsx`:
- **Akumulace / Ohřev vody (D25d, D26d, C25d, C26d)**: `TC25_001` - `TC25_004`, `TC26_001` - `TC26_004`, `TD25_001` - `TD25_009`, `TD26_001` - `TD26_009` (8 h NT)
- **Elektromobilita (D27d, C27d)**: `TC27_001`, `TD27_001` (8 h NT)
- **Smíšené / Akumulační vytápění (D35d, C35d)**: `TC35_001`, `TD35_001` (16 h NT)
- **Přímotopy (D45d, C45d, C46d)**: `TC45_001`, `TC45_002`, `TC46_001`, `TD45_001` - `TD45_005` (20 h NT)
- **Tepelná čerpadla (D55d, D57d, C55d)**: `TC55_001`, `TD55_001`, `TD57_001`, `TD57_002` (20 h až 22 h NT)
- **Víkendový tarif pro chataře (D61d)**: `TD61_001` (víkendový nepřetržitý NT)

---

## 📜 Licence

MIT License. Vytvořeno pro komunitu Home Assistant v České republice.
