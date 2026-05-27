# sustainableFoodProduction
Towards sustainable food production

Piipponen et al. (2026) evaluated the essential micronutrients, vitamins, and other nutrients provided by crops and grazing
livestock using data from USDA FoodData Central (https://fdc.nal.usda.gov/). Here we update the data.

Johannes' code supplementary_USDAnutrients.Rmd creates a lookup table of average nutrient content for products by 30 nutrients:

Vitamin A, RAE; Vitamin C, total ascorbic acid; Vitamin D (D2 + D3); Vitamin E (alpha-tocopherol); Thiamin; Riboflavin; Niacin; Vitamin B-6; Folate, total; Vitamin B-12; Pantothenic acid; Biotin; Choline, total; Calcium, Ca; Phosphorus, P; Chromium; Copper, Cu; Fluoride; Manganese, Mn; Molybdenum, Mo; Iodine, I; Iron, Fe; Magnesium, Mg; Selenium, Se; Zinc, Zn; Sodium, Na; Vitamin K (phylloquinone); Fiber, total dietary; Potassium, K; Protein.

Products categorized as:

ASF = animal-source foods
PSF = plant-source foods

- Uses on USDA nutrients database (updates every half a year)
- Takes recommended average requirement (intake) from Allen et al. (2020) [TABLE 3. Source of values for H-ARs for vitamins and minerals: IOM compared with EFSA](https://www.sciencedirect.com/science/article/pii/S2161831322002782?via%3Dihub#tbl3)

Outputs:

- nutrients_avg_asf_psf — tibble with average nutrient amounts (mg) per 100g product and per 100g protein, for both ASF (animal-source foods: meat + milk) and PSF (plant-source foods: crops)
- nutrients_for_sm — cleaned version with recommendations and % of recommended intake for both ASF and PSF




Its key output is:

Data/input/other/nutrients_avg_asf_psf.csv

Table S6 in Supplement.

![Table S6](/img/TableS6.png)

That file is then used by:

Supplementary_materials/supplementary_plot_nutrients.Rmd combines the nutrient lookup with protein rasters (ASF or PSF) from the main pipeline to create nutrient rasters.

![Difference between datasets](/img/micronutrients_change_MY_vs_Johannes.png)
