# 🐗 Zonazione PSA – Gestione aggiornamento

Questa applicazione Streamlit consente di automatizzare e validare il processo di aggiornamento del layer della **zonazione PSA** (Peste Suina Africana), direttamente integrato con **ArcGIS Online**.

## 🔐 Autenticazione
Per utilizzare l'applicazione, è necessario autenticarsi con le credenziali di ArcGIS Online. Assicurati che il tuo utente sia inserito in un gruppo con i permessi adeguati per modificare il layer della zonazione PSA.

## 🔧 Funzionalità principali

- ✔️ Aggiornamento automatico del campo `DATA`
- 🧩 Inserimento delle sigle provinciali mancanti
- 🆕 Identificazione e integrazione delle nuove province
- 📏 Calcolo dell'area (campo `KMQ`) dei poligoni
- 🗘 Assegnazione automatica del campo `AREA_PSA`
- 🧹 Pulizia dei campi amministrativi per le zone `NO_ADMIN`
- 📊 Generazione di infografiche con dati aggregati
- 📤 Caricamento e aggiornamento del file PDF del Regolamento UE