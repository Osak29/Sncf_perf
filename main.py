import pandas as pd
from sqlalchemy import create_engine
import os

#connexion a la Bd 
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME")

# Construction dynamique de l'URL
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
engine = create_engine(DATABASE_URL)



df = pd.read_csv("regularite-mensuelle-tgv-aqst.csv", sep=";")

#Coversion des dates au format de postgresql
df['Date'] = pd.to_datetime(df['Date'])

#Nettoyage des valeurs Nan
for colonne in df.columns:
    
    if df[colonne].dtype == "object":
        df[colonne] = df[colonne].fillna("")

    else :
        df[colonne] = df[colonne].fillna(0)

#Nettoyage des noms des gares 
df["Gare de départ"] = df["Gare de départ"].str.strip()
df["Gare d'arrivée"] = df["Gare d'arrivée"].str.strip()            

#Creation de la table des gares 
Gared = set(df["Gare de départ"])
Garea = set(df["Gare d'arrivée"])
Gare = Gared.union(Garea)

#Insertion des noms des gares dans la table dim_gares
Gare = pd.DataFrame(Gare, columns=["nom_gare"])
Gare.to_sql("dim_gares", engine, if_exists="append", index=False)
Gareid = pd.read_sql('SELECT * FROM dim_gares', engine)

#Insertion des liaisons 
# Gare de départ
df = df.merge(
    Gareid[["id_gare", "nom_gare"]],
    left_on="Gare de départ",
    right_on="nom_gare",
    how="left"
)

df["Gare de départ"] = df["id_gare"]
df = df.drop(columns=["id_gare", "nom_gare"])

# Gare d'arrivée
df = df.merge(
    Gareid[["id_gare", "nom_gare"]],
    left_on="Gare d'arrivée",
    right_on="nom_gare",
    how="left"
)

df["Gare d'arrivée"] = df["id_gare"]
df = df.drop(columns=["id_gare", "nom_gare"])


liaisons = df[["Gare de départ", "Gare d'arrivée","Durée moyenne du trajet", "Service"]].drop_duplicates(subset=["Gare de départ", "Gare d'arrivée"])


liaisons = liaisons.rename(columns={
    "Gare de départ" : "id_gare_depart",
    "Gare d'arrivée" : "id_gare_arrivee",
    "Durée moyenne du trajet" : "duree_moyenne_trajet",
    "Service" : "service"
})
liaisons.to_sql("dim_liaisons", engine, if_exists="append", index=False)
liaisonsId = pd.read_sql('Select * From dim_liaisons', engine)

#Insertion de la cause des retards 
cRetards = df[["Prct retard pour causes externes",
"Prct retard pour cause infrastructure",
"Prct retard pour cause gestion trafic",
"Prct retard pour cause matériel roulant",
"Prct retard pour cause gestion en gare et réutilisation de matériel",
"Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)"]] 

cRetards = cRetards.rename(columns={
"Prct retard pour causes externes" : "prct_causes_externes",
"Prct retard pour cause infrastructure" : "prct_infrastructure",
"Prct retard pour cause gestion trafic" : "prct_gestion_trafic",
"Prct retard pour cause matériel roulant" : "prct_materiel_roulant",
"Prct retard pour cause gestion en gare et réutilisation de matériel" : "prct_gestion_gare_materiel",
"Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)" : "prct_prise_en_compte_voyageurs"
})

cRetards.to_sql("dim_causes_retard", engine, if_exists="append", index=False)
cRetards = pd.read_sql('Select * From dim_causes_retard', engine)

#Insertion des fact_ponctualité

df = df.merge(
    liaisonsId[["id_liaison", "id_gare_depart", "id_gare_arrivee"]],
    left_on=["Gare de départ", "Gare d'arrivée"],
    right_on=["id_gare_depart", "id_gare_arrivee"],
    how="left"
)


fact_df = df.copy()

fact_df = fact_df.rename(columns={
    "Date": "date_liaison",
    "Nombre de circulations prévues": "nb_circulations_prevues",
    "Nombre de trains annulés": "nb_trains_annules",
    "Commentaire annulations": "commentaire_annulations",
    "Nombre de trains en retard au départ": "nb_trains_retard_depart",
    "Retard moyen des trains en retard au départ": "retard_moyen_trains_retard_depart",
    "Retard moyen de tous les trains au départ": "retard_moyen_tous_trains_depart",
    "Commentaire retards au départ": "commentaire_retards_depart",
    "Nombre de trains en retard à l'arrivée": "nb_trains_retard_arrivee",
    "Retard moyen des trains en retard à l'arrivée": "retard_moyen_trains_retard_arrivee",
    "Retard moyen de tous les trains à l'arrivée": "retard_moyen_tous_trains_arrivee",
    "Commentaire retards à l'arrivée": "commentaire_retards_arrivee",
    "Nombre trains en retard > 15min": "nb_trains_retard_plus_15min",
    "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)": "retard_moyen_plus_15min_liaison_vol",
    "Nombre trains en retard > 30min": "nb_trains_retard_plus_30min",
    "Nombre trains en retard > 60min": "nb_trains_retard_plus_60min"
})

# Liste stricte des colonnes attendues dans la table SQL fact_ponctualite
cols_fact = [
    "date_liaison",
    "id_liaison",
    "nb_circulations_prevues",
    "nb_trains_annules",
    "nb_trains_retard_depart",
    "retard_moyen_trains_retard_depart",
    "retard_moyen_tous_trains_depart",
    "nb_trains_retard_arrivee",
    "retard_moyen_trains_retard_arrivee",
    "retard_moyen_tous_trains_arrivee",
    "nb_trains_retard_plus_15min",
    "retard_moyen_plus_15min_liaison_vol",
    "nb_trains_retard_plus_30min",
    "nb_trains_retard_plus_60min",
    "commentaire_annulations",
    "commentaire_retards_depart",
    "commentaire_retards_arrivee"
]

# Filtrage pour ne conserver que les colonnes nécessaires
fact_df = fact_df[cols_fact]


fact_df.to_sql("fact_ponctualite", engine, if_exists="append", index=False)
