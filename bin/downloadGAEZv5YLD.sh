#!/usr/bin/env bash

echo Fetch GAEZv5 YLD rasters (WST)

for crop in CON COC CER CSV BRL BAN COF FDD FRT GRD MZE MAJ MLT OIL OLP OOC OCE OVG RUB PLS RSD RCW RTS COT SES SRG SOY SUB SUC SFL TEA TOB TOM WHE POT ORT; do
	gsutil cp gs://fao-gismgr-gaez-v5-data/DATA/GAEZ-V5/MAPSET/RES06-YLD/GAEZ-V5.RES06-YLD.$crop.WST.tif ~/Documents/GISdata/GAEZv5/YLD/.
done
