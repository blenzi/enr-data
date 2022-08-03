import pandas as pd
import geopandas as gpd


region_default = 'Toutes'
filieres = ['Eolien', 'Injection de biométhane', 'Méthanisation électrique', 'Photovoltaïque']

def load_installations():
    filiere = {'solaire photovoltaïque': 'Photovoltaïque',
               'éolien terrestre': 'Eolien',
               'éolien marin': 'Eolien',
               'méthanisation': 'Méthanisation électrique'
               }

    installations = gpd.read_file('data/registre.gpkg', layer='registre').to_crs(epsg=4326)\
        .assign(Filière=lambda x: x['typo'].replace(filiere), energie_GWh=lambda x: x['prod_MWh_an'] * 1e-3)\
        .rename(columns={'millesime': 'annee'}).astype({'annee': 'int'})

    columns = ['nominstallation', 'Filière', 'typo', 'date_inst', 'puiss_MW', 'energie_GWh',
               'NOM_EPCI', 'NOM_DEP', 'NOM_REG', 'EPCI', 'DEPARTEMENTS_DE_L_EPCI', 'annee', 'geometry']
    return pd.concat([installations.loc[installations['Filière'].isin(filieres)], load_installations_biogaz()])[columns]

def load_installations_biogaz():
    return gpd.read_file('data/registre.gpkg', layer='installations_biogaz')\
        .to_crs(epsg=4326)\
        .rename(columns={'nom_du_projet': 'nominstallation',
                         'date_de_mes': 'date_inst',
                         'quantite_annuelle_injectee_en_mwh': 'prod_MWh_an',
                         'type': 'typo'}) \
        .assign(Filière='Injection de biométhane',
                puiss_MW=lambda x: x['capacite_de_production_gwh_an'] / (365 * 24) * 1e3,
                energie_GWh=lambda x: x['prod_MWh_an'] * 1e-3
                ) \
        .astype({'annee': 'int'})


def get_indicateurs_registre(installations):
    # Indicateurs pour toute la France et aux niveaux EPCI, départements, régions
    def get_sum(df):
        return df.agg(puiss_MW=("puiss_MW", 'sum'), energie_GWh=("energie_GWh", 'sum'), N=("puiss_MW", 'count')) \
            .reset_index() \
            .assign(type_estimation='Somme') \
            .rename(columns={'N': 'Nombre de sites'})

    France = get_sum(installations.groupby(['annee', 'Filière'])).assign(Zone=region_default, TypeZone='Régions')

    ind = [get_sum(installations.groupby(['annee', 'Filière', column])).rename(columns={column: 'Zone'}) \
               .assign(TypeZone=type_zone)
           for type_zone, column in {'Epci': 'NOM_EPCI', 'Départements': 'NOM_DEP', 'Régions': 'NOM_REG'}.items()]

    return pd.concat([France, *ind])

def get_indicateurs_sdes():
    return pd.read_csv('data/SDES_indicateurs_depts_regions_France.csv') \
        .set_index('Zone').drop('Total DOM').reset_index() \
        .replace({'Total France': 'Toutes', 'Somme': 'Régions'}) \
        .rename(columns={'Filiere.de.production': 'Filière'}) \
        .pivot_table(index=['TypeZone', 'Zone', 'Filière', 'annee'],
                     values='valeur',
                     columns='indicateur') \
        .assign(puiss_MW=lambda x: x['Puissance.totale.en.kW'] / 1e3, type_estimation='SDES') \
        .drop(columns=['Puissance.totale.en.kW'])

def get_indicateurs(installations):
    indicateurs = get_indicateurs_registre(installations)
    sdes = get_indicateurs_sdes()

    # Add 'energie_GWh' to SDES and concat with indicateurs, keeping it as default
    _ = pd.concat([sdes, indicateurs.set_index(sdes.index.names)['energie_GWh']], join='inner', axis=1).reset_index()
    return pd.concat([indicateurs, _]) \
        .drop_duplicates(['TypeZone', 'Zone', 'annee', 'Filière'], keep='last').astype({'annee': int})

installations = load_installations()
indicateurs = get_indicateurs(installations)

# Collect EPCIs and dump to epcis.csv
def fcn(x):
    "Converti 'DEPARTEMENTS_DE_L_EPCI' en liste"
    return x.replace('\"', '').strip('c()').split(', ')

multi = installations['DEPARTEMENTS_DE_L_EPCI'].str.contains('c')
epcis = installations.loc[:, ['EPCI', 'NOM_EPCI', 'DEPARTEMENTS_DE_L_EPCI']]
epcis.loc[multi, 'DEPARTEMENTS_DE_L_EPCI'] = epcis.loc[multi, 'DEPARTEMENTS_DE_L_EPCI'].apply(fcn)
epcis.explode('DEPARTEMENTS_DE_L_EPCI').drop_duplicates().dropna().to_csv('data/epcis.csv', index=False)

# Export installations and indicateurs
installations[~installations.geometry.is_empty & (installations['annee'] == installations['annee'].max())]\
    .to_file('data/app.gpkg', layer='installations')  # TODO: drop columns
indicateurs.to_csv('data/indicateurs.csv', index=False)
