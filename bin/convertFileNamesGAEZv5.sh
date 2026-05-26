#!/usr/bin/env bash

echo Rename files...



#  "ALF" "BAN" "BCK" "BRL" "BSG" "CAB" "CAR" "CHK" "CIT" "COC" "COF" "CON" "COT" "COW" "CSV" "FLX" "FML" "GRD" "GRM" "JTR" "MIS" "MZE" "NAP" "OAT" "OLP" "OLV" "ONI" "PEA" "PHB" "PIG" "PML" "RCD" "RCG" "RCW" "RSD" "RUB" "RYE" "SFL" "SOY" "SPO" "SRG" "SUB" "SUC" "SWG" "TEA" "TOB" "TOM" "WHE" "WPO" "YAM"


items=(
  ALF BAN BCK BRL BSG CAB CAR CHK CIT COC COF CON COT
  COW CSV FLX FML GRD GRM JTR MIS MZE NAP OAT OLP OLV
  ONI PEA PHB PIG PML RCD RCG RCW RSD RUB RYE SFL SOY
  SPO SRG SUB SUC SWG TEA TOB TOM WHE WPO YAM
)

for item in "${items[@]}"; do
  lower_item="$(printf '%s' "$item" | tr '[:upper:]' '[:lower:]')"

#  echo "cp /Users/myliheik/Documents/GISdata/GAEZv5/YCX/GAEZ-V5.RES05-YCX.HP0120.AGERA5.HIST.${item}.LRLM.tif  ~/Documents/projektit/2025-Water-Food-Futures/Piipponen/article_griddedprot/Data/Input/gaez/GAEZ-V5-RES05-YCX-HP0120-AGERA5-HIST-SUB-LRLM/ycLr_${lower_item}.tif"
cp /Users/myliheik/Documents/GISdata/GAEZv5/YCX/GAEZ-V5.RES05-YCX.HP0120.AGERA5.HIST.${item}.LRLM.tif  ~/Documents/projektit/2025-Water-Food-Futures/Piipponen/article_griddedprot/Data/Input/gaez/GAEZ-V5-RES05-YCX-HP0120-AGERA5-HIST-SUB-LRLM/ycLr_${lower_item}.tif
 
done

# Napier grass is high input!
cp /Users/myliheik/Documents/GISdata/GAEZv5/YCX/GAEZ-V5.RES05-YCX.HP0120.AGERA5.HIST.NAP.HRLM.tif  ~/Documents/projektit/2025-Water-Food-Futures/Piipponen/article_griddedprot/Data/Input/gaez/GAEZ-V5-RES05-YCX-HP0120-AGERA5-HIST-SUB-LRLM/ycHr_nap.tif
