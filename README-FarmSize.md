# Farm size 


Following article: Julie Fortin et al 2026 Environ. Res.: Food Syst. 3 014501

DOI 10.1088/2976-601X/ae3e93

https://iopscience.iop.org/article/10.1088/2976-601X/ae3e93

>There is consensus at the global international level as to the definition of an agricultural holding and what type of land counts toward the farm’s size: ‘land used for growing crops (temporary and permanent), meadows and pastures, and fallow land; unutilized agricultural land; forest and other wooded land; bodies of water; farmyards and land occupied by farm buildings; and land for which a holding does not have any rights to agricultural use, except for the products of the trees grown on it’ [1]. Nevertheless, national censuses are not always consistent nor transparent in their definitions of farm size, affecting cross-country comparisons and analyses. Hence, for transparency, we documented the definition of farm size provided by each data source, if available, in the dataset and in the metadata.


>We harmonized all data to common variables: (1) administrative unit name, (2) measurement unit, (3) reporting year, and (4) farm size. 

>We calibrated the dataset to the years 2000, 2010 and 2020 using national farm size trends derived from FAO WCA rounds.


## Data:

The data (GlobalFarmSize_Dataset_v1.1.0.zip) was downloaded from Zenodo: https://zenodo.org/records/17550107

This file was used:
Output/Dataset/GlobalFarmSizeDataset_Calibrated.shp

We set farm size values to years: 1992, 1996, 2000, 2004, 2008, 2012, 2016, 2020 such that we copied the nearest calibrated mean farm size (ha) per administrative region (either 2000, 2010, or 2020) from Fortin.

See notebooks/Adjust-Fortin-2026-farm-size-dataset for details and illustrative plots.

