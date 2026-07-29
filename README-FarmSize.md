# Farm size 


Following article: **[Julie Fortin et al 2026 Environ. Res.: Food Syst. 3 014501.
DOI 10.1088/2976-601X/ae3e93](https://iopscience.iop.org/article/10.1088/2976-601X/ae3e93)**

Fortin says:
>There is consensus at the global international level as to the definition of an agricultural holding and what type of land counts toward the farm’s size: ‘land used for growing crops (temporary and permanent), meadows and pastures, and fallow land; unutilized agricultural land; forest and other wooded land; bodies of water; farmyards and land occupied by farm buildings; and land for which a holding does not have any rights to agricultural use, except for the products of the trees grown on it’ [1]. Nevertheless, national censuses are not always consistent nor transparent in their definitions of farm size, affecting cross-country comparisons and analyses. Hence, for transparency, we documented the definition of farm size provided by each data source, if available, in the dataset and in the metadata.


>We harmonized all data to common variables: (1) administrative unit name, (2) measurement unit, (3) reporting year, and (4) farm size. 

>We calibrated the dataset to the years 2000, 2010 and 2020 using national farm size trends derived from FAO WCA rounds.


## Data:

The data (GlobalFarmSize_Dataset_v1.1.0.zip) was downloaded from Zenodo: **[https://zenodo.org/records/17550107](https://zenodo.org/records/17550107)**

This file was used:
Output/Dataset/GlobalFarmSizeDataset_Calibrated.shp

Initially we considered using Fortin's estimates for 2010 and 2020 (CALIB-variables) to estimate the full time series 1992-2020, but the data did not look convincing, see details in **[notebooks/Adjust-Fortin-2026-farm-size-dataset](notebooks/Adjust-Fortin-2026-farm-size-dataset.ipynb)**.

We used the mean farm size (ha) per administrative region of FAO WCA round 2000 from Fortin dataset. WCA is anchored to a census year 2000, but the true source year is some time between 1995-2005. These ADM1 regional observations are extended to annual series by using LINEQ country-level mean farm-size trajectories, which are available for 0-4 FAO WCA rounds. LINEQ is first interpolated into continuous 1986-2023 time series. When a country has <= 1 LINEQ observations, the script falls back to a broader subregional trend derived from the median country pattern within each SUBSUBREG. Each Fortin regional observation is then propagated backward and forward through time using the relevant country or subregional growth rates, producing annual farm-size estimates for every ADM1 unit. Remaining missing regions are filled using geographically nearest or touching donor regions, and the final product is exported as both a GeoPackage and a global multiband raster.


See **[notebooks/Adjust-ADM1-Fortin-with-ADM0-LINEQ-2026-farm-size.ipynb](notebooks/Adjust-ADM1-Fortin-with-ADM0-LINEQ-2026-farm-size.ipynb)**  for details and illustrative plots.


