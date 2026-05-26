#!/usr/bin/env bash

echo Fetch GAEZv5 PRD rasters

# descriptions: OCE (Other cerials) ORT (Yams (and other minor root crops)) PLS (Pulses) POT (White potato, Sweet potato) RCW Rise RSD (Rapeseed) RUB (Para rubber)
# CER (Cereal crops (1-7)) COF (Coffee) COT (Seed cotton) FDD (Fodder crops) MAJ (Major crops) NES (All other crops, like spices, fibre crops) OIL (Oil crops) OLP (Oil palm fruit)
# OOC (Olives and other minor oil crops) OVG (Other vegetables (i.e. all vegetables except tomato)) RTS (Root and tuber crops (8-9)) SES (Sesame seed) SFL (Sunflower seed)
# SUB (Sugar beet) SUC (Sugarcane) TEA TOB (Tobacco) 


# list of crops: 
list="BAN BRL CER COC COF CON COT CSV FDD FRT GRD MLT MZE NES OCE OIL OLP OOC ORT OVG PLS POT RCW RSD RTS RUB SES SFL SOY SRG SUB SUC TEA TOB TOM WHE"
#list="BAN BRL CER COC COF CON COT CSV FDD FRT GRD MAJ MLT MZE NES OCE OIL OLP OOC ORT OVG PLS POT RCW RSD RTS RUB SES SFL SOY SRG SUB SUC TEA TOB TOM WHE"
#list="BAN BRL COC CON CSV FRT GRD MLT MZE OCE ORT PLS POT RCW RSD SOY SRG TOB TOM WHE" # 20

# perfect_match and partial_match (13):
#list="BAN BRL CON CSV GRD MLT MZE OVG POT RCW SOY SRG WHE"
#puuttuu CHK COW PHB PIG YAM PEA CAB ONI CIT

# WSI (Water Supply Irrigated): Represents cultivated areas under full irrigation management.
# WSR (Water Supply Rain-fed): Represents cultivated areas relying solely on rainfall.
# WST (Water Supply Total/Mixed): Often refers to a total or combined assessment of both rain-fed and irrigated conditions

echo We take WST (Water Supply Total/Mixed): Often refers to a total or combined assessment of both rain-fed and irrigated conditions

for CROP in $list; do
  echo $CROP
  gsutil cp gs://fao-gismgr-gaez-v5-data/DATA/GAEZ-V5/MAPSET/RES06-PRD/GAEZ-V5.RES06-PRD.$CROP.WST.tif ~/Documents/GISdata/GAEZv5/.
done




