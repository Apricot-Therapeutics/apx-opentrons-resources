from opentrons import protocol_api
import pandas as pd

# metadata
metadata = {
    "protocolName": "OVP Drug Transfer to 384-well Cell Plate",
    "description": """This protocol is used to transfer drugs from a
     pre-prepared drug plate to a 384 well plate containing patient cells 
     (in 45 ul of media) in a randomized layout.""",
    "author": "Adrian Tschan"
    }

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.16"}

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    # load labware
    tips = protocol.load_labware("opentrons_96_filtertiprack_20ul", 1)
    drug_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    cell_plate = protocol.load_labware("corning_384_wellplate_112ul_flat", 3)

    # optional: set liquids
    sample = protocol.define_liquid(name="sample", display_color="#1c03fc",
                                    description="sample to which to add drugs")
    drugs = protocol.define_liquid(name="drugs", display_color="#fcba03",
                                 description="drugs to be transferred")

    # load drugs into 96-well plate
    for well in drug_plate.wells():
        well.load_liquid(liquid=drugs, volume=1000)

    # load sample into 384-well plate
    for i_row, row in enumerate(cell_plate.rows()):
        if i_row > 1 and i_row < 14:
            for i_well, well in enumerate(row):
                if i_well > 1 and i_well < 23:
                    well.load_liquid(liquid=sample, volume=45)


    # initialize pipette
    left_pipette = protocol.load_instrument("p20_single", "left",
                                            tip_racks=[tips])

    # load the drug layout on drug master plate and final 384-well plate
    drug_layout_96 = pd.read_csv(r"K:\projects\OV_Precision\documents\plate_layout\drug_plate_layout_v1.0.csv")
    drug_layout_384 = pd.read_csv(r"K:\projects\OV_Precision\documents\plate_layout\plate_metadata_v1.0.csv")



    # transfer diluent from reservoir to plate
    left_pipette.transfer(100, reservoir["A1"], plate.wells(),
                          mix_after=(3, 50))
