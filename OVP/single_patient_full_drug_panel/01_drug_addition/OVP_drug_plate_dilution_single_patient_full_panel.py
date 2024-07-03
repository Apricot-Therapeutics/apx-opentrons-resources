from opentrons import protocol_api
import pandas as pd
from sys import platform

# metadata
metadata = {
    "protocolName": "OVP Drug Plate Dilution",
    "description": """This protocol is used to dilute drugs on a
     pre-prepared 96-well drug plate containing 5 ul of drug per well to a 
     1:100 dilution by adding 495 ul of RPMI medium.""",
    "author": "Adrian Tschan"
    }

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.16"}

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    # load labware
    # TO-DO: change labware to match actual labware used
    tips = protocol.load_labware("opentrons_96_filtertiprack_1000ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    drug_plate = protocol.load_labware("thermoscientific_96_wellplate_1300ul", 5)

    # for local testing
    #drug_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)

    # optional: set liquids
    media = protocol.define_liquid(name="RPMI", display_color="#1c03fc",
                                    description="media to dilute the drugs")
    drugs = protocol.define_liquid(name="drugs", display_color="#fcba03",
                                 description="drugs to be transferred")

    # load some metadata we need later
    if platform == "win32":
        # load the drug layout on drug master plate
        drug_plate_layout = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\Apricot\OVP\single_patient_plate\drug_plate_metadata_v1.3.csv")
    elif platform == "linux":
        # load the drug layout on drug master plate
        drug_plate_layout = pd.read_csv("/data/user_storage/apricot_data/drug_plate_metadata_v1.3.csv")


    # load drugs into 96-well plate
    for i, well in drug_plate_layout.iterrows():
        well = drug_plate[well.row + str(well.col)]
        well.load_liquid(liquid=drugs, volume=5)

    # load media into reservoir
    reservoir['A1'].load_liquid(liquid=media, volume=10000)
    reservoir['A2'].load_liquid(liquid=media, volume=10000)

    # initialize pipette
    left_pipette = protocol.load_instrument("p300_multi_gen2", "left",
                                            tip_racks=[tips])
    right_pipette = protocol.load_instrument("p1000_single_gen2", "right",
                                            tip_racks=[tips])

    # set well clearance of pipettes
    left_pipette.well_bottom_clearance.aspirate = 1.5
    left_pipette.well_bottom_clearance.dispense = 1.5
    right_pipette.well_bottom_clearance.aspirate = 1.5
    right_pipette.well_bottom_clearance.dispense = 1.5

    for i, drug in drug_plate_layout.iterrows():
        if i < 16:
            source_well = 'A1'
        else:
            source_well = 'A2'

        destination_well = drug.row + str(drug.col)

        print(f"diluting {drug.condition} in well {drug.well}")

        # distribute from source well to dest wells
        right_pipette.transfer(volume=495,
                               source=reservoir[source_well],
                               dest=drug_plate[destination_well],
                               mix_after=(3, 400))

