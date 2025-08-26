# Import Zonazione PSA – Consolida aggiornamento
import streamlit as st
from arcgis.gis import GIS
from arcgis.features import GeoAccessor, GeoSeriesAccessor
from datetime import datetime
# Import Generazione infografiche
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import os

# === CONFIGURAZIONE LAYOUT ===
st.set_page_config(page_title="Zonazione PSA", layout="wide", initial_sidebar_state="expanded")
st.header("🐗 Zonazione PSA – Gestione aggiornamento")

# === DESCRIZIONE APPLICAZIONE ===
st.markdown("""
<p style='font-size: 16px;'>
Questa applicazione va utilizzata dopo aver effettuato le modifiche al layer della zonazione attraverso l'editor dedicato ed automatizza il controllo di coerenza dei dati.
Operazioni eseguite:
<ul>
<li>Aggiornamento della data di riferimento</li>
<li>Inserimento delle sigle provinciali mancanti</li>
<li>Identificazione e integrazione di nuove province</li>
<li>Ricalcolo delle superfici in km²</li>
<li>Assegnazione dell'area PSA sulla base dei raggruppamenti di regioni</li>
<li>Pulizia dei campi amministrativi non rilevanti per le zone NO_ADMIN</li>
<li>Generazione di infografiche basate sui dati aggiornati</li>
<li>Caricamento del regolamento UE aggiornato</li>
</ul>
</p>
""", unsafe_allow_html=True)

# === INIZIALIZZAZIONE SESSIONE ===
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'gis' not in st.session_state:
    st.session_state.gis = None

# === LOGIN ===
with st.sidebar:
    st.subheader("🔐 Connessione a ArcGIS Online")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        login_button = st.form_submit_button("Accedi", use_container_width=True)
        logout_button = st.form_submit_button("Logout", use_container_width=True)


        if login_button:
            try:
                gis = GIS("https://izsam.maps.arcgis.com", username=username, password=password)
                st.session_state.gis = gis
                st.session_state.logged_in = True
                st.success("✔️ Connessione effettuata con successo.")
            except Exception as e:
                st.error(f"❌ Errore durante la connessione: {e}")

        if logout_button:
            st.session_state.logged_in = False
            st.session_state.gis = None
            st.info("🔒 Logout effettuato.")

# === AVVIO FLUSSO ===
if st.session_state.logged_in:
    tab1, tab2, tab3 = st.tabs(["📦 Consolida aggiornamento", "📊 Genera infografiche",":bookmark_tabs: Carica regolamento UE"])
    with tab1:
        st.markdown("""
        <p style='font-size: 16px;'>
        Questa sezione consente di avviare il flusso di consolidamento dell'aggiornamento della zonazione PSA.
        </p>
        """, unsafe_allow_html=True)
    

        if st.button("Avvia il consolidamento"):

            # === CARICAMENTO DATI ===
            with st.spinner("Caricamento contenuti..."):
                gis = st.session_state.gis
                item_zonazione = gis.content.get(st.secrets["ID_HFL_ZONAZIONE"])
                item_comuni = gis.content.get(st.secrets["ID_HFL_COMUNI"])
                item_tabella_prov = gis.content.get(st.secrets["ID_HFT_PROVINCE"])
            st.markdown('<span style="color:green">✔️ Contenuti caricati correttamente</span>', unsafe_allow_html=True)


            # === AGGIORNAMENTO CAMPO DATA ===
            st.markdown("*📅 Aggiornamento campo DATA...*")
            today = datetime.now().strftime('%d-%m-%Y')
            item_zonazione.layers[0].calculate(where="1=1", calc_expression={"field": "DATA", "value": today})
            st.markdown(f'<span style="color:green">✔️ Data aggiornata a: {today}</span>', unsafe_allow_html=True)

            # === FIX SIGLA PROVINCIA ===
            st.markdown("*🧩 Verifica sigla provincia mancante...*")
            zone_no_sigla = item_zonazione.layers[0].query(where="PROV=Null", out_fields="*", out_sr=4326, as_df=True)
            if len(zone_no_sigla) == 0:
                st.markdown('<span style="color:#1f77b4">✔️ Nessuna sigla da aggiornare</span>', unsafe_allow_html=True)
            else:
                comuni = item_comuni.layers[0].query(
                    where=f"ISTAT IN ({','.join(zone_no_sigla['ISTAT'])})",
                    out_fields="ISTAT, COMUNE, SIGLA_PROVINCIA",
                    return_geometry=False,
                    as_df=True
                )
                for istat, sigla in zip(comuni['ISTAT'], comuni['SIGLA_PROVINCIA']):
                    item_zonazione.layers[0].calculate(
                        where=f"ISTAT = '{istat}'",
                        calc_expression={"field": "PROV", "value": sigla}
                    )
                st.markdown(f'<span style="color:green">✔️ Aggiornate le sigle provincia per {len(comuni)} comuni</span>', unsafe_allow_html=True)

            # === INSERIMENTO NUOVE PROVINCE ===
            st.markdown("*🆕 Ricerca nuove province...*")
            prov_zonazione = item_zonazione.layers[0].query(where="1=1", out_fields="REGIONE, PROV", return_geometry=False, return_distinct_values=True, as_df=True)
            prov_reference = item_tabella_prov.tables[0].query(as_df=True)
            nuove_province = list(set(prov_zonazione['PROV']) - set(prov_reference['PROV']))
            if nuove_province:
                nuove_province_str = "','".join(nuove_province)
                comuni_da_escludere = item_zonazione.layers[0].query(where=f"PROV IN ('{nuove_province_str}')", out_fields="ISTAT", as_df=True)
                comuni_da_escludere_str = "','".join(comuni_da_escludere['ISTAT'].to_list())
                nuovi_comuni_lim = item_comuni.layers[0].query(
                    where=f"SIGLA_PROVINCIA IN ('{nuove_province_str}') AND ISTAT NOT IN ('{comuni_da_escludere_str}')",
                    as_df=True
                )
                new_lim = nuovi_comuni_lim[['REGIONE','PROVINCIA','SIGLA_PROVINCIA','COMUNE','ISTAT','Shape__Area','Shape__Length','SHAPE']].copy()
                new_lim.rename(columns={'SIGLA_PROVINCIA': 'PROV'}, inplace=True)
                new_lim['ZONA_RESTR'] = 'LIM'
                new_lim['AREA_PSA'] = None
                new_lim['ORIGINE'] = 'ADMIN'
                new_lim['DATA'] = today
                new_lim['KMQ'] = None
                new_lim = new_lim.reindex(columns=['REGIONE', 'PROVINCIA', 'PROV', 'COMUNE', 'ISTAT', 'ZONA_RESTR','AREA_PSA', 'ORIGINE', 'DATA', 'KMQ', 'Shape__Area', 'Shape__Length','SHAPE'])
                item_zonazione.layers[0].edit_features(adds=new_lim)
                new_prov = new_lim[['REGIONE','PROV']].drop_duplicates().reset_index(drop=True)
                item_tabella_prov.tables[0].edit_features(adds=new_prov)
                st.markdown(f'<span style="color:green">✔️ Aggiunte nuove province: {", ".join(nuove_province)}</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span style="color:#1f77b4">✔️ Nessuna nuova provincia trovata</span>', unsafe_allow_html=True)

            # === CALCOLO KMQ ===
            st.markdown("*📏 Ricalcolo campo KMQ...*")
            zone_no_kmq = item_zonazione.layers[0].query(where="KMQ=Null", out_fields="*", out_sr=32632, as_df=True)
            if len(zone_no_kmq) == 0:
                st.markdown('<span style="color:#1f77b4">✔️ Tutte le zone hanno KMQ valorizzato</span>', unsafe_allow_html=True)
            else:
                count = 0
                for fid, area in zip(zone_no_kmq['FID'], GeoSeriesAccessor(zone_no_kmq['SHAPE']).area):
                    item_zonazione.layers[0].calculate(
                        where=f"FID = '{fid}'",
                        calc_expression={"field":"KMQ", "value": round(area/10**6, 3)}
                    )
                    count += 1
                st.markdown(f'<span style="color:green">✔️ Calcolato KMQ per {count} poligoni</span>', unsafe_allow_html=True)

            # === ASSEGNAZIONE AREA_PSA ===
            st.markdown("*🗘️ Assegnazione AREA_PSA...*")
            lista_PL = ['PIEMONTE','LIGURIA','LOMBARDIA','EMILIA ROMAGNA','TOSCANA']
            lista_CL = ['CALABRIA']
            lista_CA = ['CAMPANIA','BASILICATA']
            zone_no_area = item_zonazione.layers[0].query(where="AREA_PSA=Null", out_fields="*", out_sr=4326, as_df=True)
            count = 0
            for fid, regione in zip(zone_no_area['FID'], zone_no_area['REGIONE']):
                if regione in lista_PL:
                    area = 'PL'
                elif regione in lista_CL:
                    area = 'CL'
                elif regione in lista_CA:
                    area = 'CA'
                else:
                    continue
                item_zonazione.layers[0].calculate(where=f"FID = '{fid}'", calc_expression={"field":"AREA_PSA", "value":area})
                count += 1
            if count == 0:
                st.markdown('<span style="color:#1f77b4">✔️ Tutte le zone hanno AREA_PSA valorizzato</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span style="color:green">✔️ Assegnata AREA_PSA a {count} zone</span>', unsafe_allow_html=True)

            # === PULIZIA CAMPI NO_ADMIN ===
            st.markdown("*🛉 Pulizia campi zone NO_ADMIN...*")
            for campo in ['PROVINCIA','COMUNE']:
                item_zonazione.layers[0].calculate(where="ORIGINE = 'NO_ADMIN'", calc_expression={"field": campo, "value": None})
            st.markdown('<span style="color:green">✔️ Pulizia completata</span>', unsafe_allow_html=True)

            # === CONCLUSIONE ===
            st.markdown('<h4 style="color:green">🎉 Tutto completato! Il layer della zonazione è stato aggiornato correttamente.</h4>', unsafe_allow_html=True)
        
        with tab2:
            st.markdown("""
            <p style='font-size: 16px;'>
            Questa sezione consente di generare le infografiche basate sui dati aggiornati della zonazione PSA. <b>Assicurati di aver eseguito prima il consolidamento</b>.
            </p>
            """, unsafe_allow_html=True)

            if st.button("Avvia generazione"):
                gis = st.session_state.gis
                item_zonazione = gis.content.get(st.secrets["ID_HFL_ZONAZIONE"])
                sdf = item_zonazione.layers[0].query(
                    where="ZONA_RESTR IN ('I','II','III')",
                    out_fields="ZONA_RESTR, AREA_PSA, KMQ",
                    return_geometry=False,
                    as_df=True
                )

                grouped = sdf.groupby(['AREA_PSA', 'ZONA_RESTR'])['KMQ'].sum().unstack().fillna(0)
                colori_zone = {'I': '#4E7824', 'II': '#C9D787', 'III': '#7D945D'}
                zone_order = ['I', 'II', 'III']
                aree = grouped.index.tolist()

                def crea_fig(labels_prefix, lang):
                    fig, axes = plt.subplots(1, len(aree), figsize=(20, 6), facecolor='#F2F6ED')
                    if len(aree) == 1:
                        axes = [axes]
                    for i, area in enumerate(aree):
                        valori = grouped.loc[area, zone_order]
                        vals = [val for val in valori if val > 0]
                        zones = [z for z in zone_order if valori[z] > 0]
                        colors = [colori_zone[z] for z in zones]
                        labels = [f"{labels_prefix} {z}:\n{valori[z]:.1f} km²" for z in zones]
                        wedges, texts = axes[i].pie(
                            vals,
                            labels=labels,
                            colors=colors,
                            startangle=90,
                            counterclock=False,
                            wedgeprops={'width': 0.25, 'edgecolor': 'white'},
                            labeldistance=1.2,
                            textprops={'fontsize': 18}
                        )
                        for j, p in enumerate(wedges):
                            ang = (p.theta2 - p.theta1)/2 + p.theta1
                            x, y = np.cos(np.deg2rad(ang)), np.sin(np.deg2rad(ang))
                            conn = f"angle,angleA=0,angleB={ang}"
                            axes[i].annotate("", xy=(x*0.8, y*0.8), xytext=(x*1.1, y*1.1),
                                            arrowprops=dict(arrowstyle='-', connectionstyle=conn, color='gray'))
                        axes[i].text(0, 0, area, ha='center', va='center', fontsize=60, weight='bold', color='#4E7824')
                        axes[i].set_title('')
                    plt.tight_layout()

                    # Calcola il dpi massimo per rimanere entro 4999 px in larghezza
                    width_inch = fig.get_size_inches()[0]
                    dpi = min(300, int(4999 / width_inch))

                    path = f"infografica_psa_{lang}.png"
                    fig.savefig(path, format='png', dpi=dpi, bbox_inches='tight', facecolor=fig.get_facecolor())
                    return path

                path_it = crea_fig('Zona', 'IT')
                path_en = crea_fig('Zone', 'EN')

                tab_g1, tab_g2 = st.tabs(["Infografiche", "Dati aggregati"])

                with tab_g1:
                    st.markdown("<h3>Infografiche</h3>", unsafe_allow_html=True)
                    st.image(path_it, caption="Infografica in Italiano", use_container_width=True)
                    st.image(path_en, caption="Infographic in English", use_container_width=True)

                with tab_g2:
                    df_reset = grouped.reset_index().melt(id_vars='AREA_PSA', var_name='ZONA_RESTR', value_name='KMQ')
                    st.markdown("<h3>Dati aggregati</h3>", unsafe_allow_html=True)
                    st.dataframe(df_reset, use_container_width=True)
                    st.download_button("Scarica dati aggregati", df_reset.to_csv(index=False).encode('utf-8'), "dati_aggregati.csv", "text/csv")

                # === AGGIORNA GLI ITEM SU AGOL ===
                st.markdown("<h4>🔄 Sovrascrittura degli item online...</h4>", unsafe_allow_html=True)
                items_it_en = {
                    "IT": "a6ae9e97f1514e3c88584f6a38453898",
                    "EN": "1d5effaac9bc48b99c82e66fda183d57"
                }
                for lang, item_id in items_it_en.items():
                    file_path = f"infografica_psa_{lang}.png"
                    item = gis.content.get(item_id)
                    item.update(data=file_path)
                    os.remove(file_path)
                st.success("✔️ Infografiche aggiornate su ArcGIS Online")

            with tab3:
                st.markdown("""
                <p style='font-size: 16px;'>
                Questa sezione consente di caricare il regolamento UE aggiornato per la zonazione PSA.
                </p>
                """, unsafe_allow_html=True)

                uploaded_file_it = st.file_uploader("Carica il file del regolamento UE in Italiano", type=["pdf"])
                if uploaded_file_it is not None:
                    with open("regolamento_psa_IT.pdf", "wb") as f:
                        f.write(uploaded_file_it.getbuffer())
                    if st.button("Carica file IT"):
                        try:
                            item = st.session_state.gis.content.get("7f7f51d88faa4d5b8b4272b6c4b8c382")
                            item.update(data="regolamento_psa_IT.pdf")
                            os.remove("regolamento_psa_IT.pdf")
                            st.success("✔️ File in italiano aggiornato con successo su ArcGIS Online!")
                        except Exception as e:
                            st.error(f"❌ Errore durante il caricamento: {e}")

                uploaded_file_en = st.file_uploader("Carica il file del regolamento UE in English", type=["pdf"])
                if uploaded_file_en is not None:
                    with open("regolamento_psa_EN.pdf", "wb") as f:
                        f.write(uploaded_file_en.getbuffer())
                    if st.button("Carica file EN"):
                        try:
                            item = st.session_state.gis.content.get("757a24d70e6d42b3a0b881914f6ccb71")
                            item.update(data="regolamento_psa_EN.pdf")
                            os.remove("regolamento_psa_EN.pdf")
                            st.success("✔️ File in inglese aggiornato con successo su ArcGIS Online!")
                        except Exception as e:
                            st.error(f"❌ Errore durante il caricamento: {e}")

