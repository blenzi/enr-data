# Collecte de données pour l'outil EnR

Récupération des données de l'outil [TEO](https://gitlab.com/dreal-datalab/enr_reseaux_teo/) et la version adaptée à toute la France ([lien](https://gitlab.com/blenzi/enr_reseaux_teo)) pour 
alimenter le tableau de bord [enr-app](https://github.com/blenzi/enr-app).

Ce module produit des fichiers contenant les installations de production d'électricité et injection de biométhane 
et des indicateurs (puissance, énergie produite et nombre d'installations) associés, à partir du registre ODRE + GRDF 
et des tableaux du SDES. 

## Installation

Python 3.8+ et [pip](https://pip.pypa.io/en/stable/) sont nécessaires.

```shell
git clone https://github.com/blenzi/enr-data.git
pip install -e enr-data/.
```

## Running

### Installation des modules R

L'installation des modules nécessaires à l'outil [TEO](https://gitlab.com/dreal-datalab/enr_reseaux_teo/) peut 
se faire avec le fichier [install.sh](https://gitlab.com/blenzi/enr_reseaux_teo/-/blob/master/install.sh).

### Installations du registre ODRE + GRDF

Pour extraire la liste des installations:

```R
library(rmarkdown)
library(tidyr)
library(sf)
library(dplyr)

render('collecte/registre/registre_odre_31122021.Rmd', knit_root_dir=getwd())
render('collecte/registre_biogaz/registre_biogaz.Rmd', knit_root_dir=getwd())

load("collecte/registre/indic_registre_prod_elec_renouv_r52.RData")
st_write(registre8 %>% mutate(DEPARTEMENTS_DE_L_EPCI=as.character(DEPARTEMENTS_DE_L_EPCI), REGIONS_DE_L_EPCI=as.character(REGIONS_DE_L_EPCI)), 'registre.gpkg', 'registre')

load("collecte/registre_biogaz/registre_biogaz_Fr_2021.RData")
registre_biogaz_deplie <- unnest(registre_biogaz, cols = data_annuelles)
st_write(registre_biogaz_deplie %>% select(-geom) %>% mutate(DEPARTEMENTS_DE_L_EPCI=as.character(DEPARTEMENTS_DE_L_EPCI), REGIONS_DE_L_EPCI=as.character(REGIONS_DE_L_EPCI)), 'registre.gpkg', 'installations_biogaz')
```

### Contours pour les cartes

Pour obtenir les contours des régions, départements et EPCIs, il faut également tourner la collecte complète en 
utilisant la branche [collecte](https://gitlab.com/blenzi/enr_reseaux_teo/-/blob/collecte) et ensuite:

```R
library(sf)
library(dplyr)

load('app/data_appli.RData')
st_write(carto_reg, 'app.gpkg', 'regions')
st_write(carto_dep, 'app.gpkg', 'departements')
st_write(carto_epci, 'app.gpkg', 'EPCIs')
```

et copier `app.gpkg` dans `data/`

### Production des fichiers pour le tableau de bord

Copier le fichier `data/SDES_indicateurs_depts_regions_France.csv` dans `data/`

```shell
cd enr-data
mkdir data/
python enr_data/registre.py
```
