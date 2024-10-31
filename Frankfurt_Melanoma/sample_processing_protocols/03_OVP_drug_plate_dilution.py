from opentrons import protocol_api
import pandas as pd
from sys import platform

# metadata
metadata = {
    "protocolName": "OVP Drug Plate Dilution",
    "description": """This protocol is used to dilute drugs on a
     pre-prepared 96-well drug plate containing 3 ul of drug per well to a 
     1:100 dilution by adding 297 ul of RPMI medium.""",
    "author": "Adrian Tschan"
    }

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.18"}

def add_parameters(parameters: protocol_api.Parameters):

    parameters.add_str(
    variable_name="pipette_position",
    display_name="p300 8-channel position",
    description="Which mount is the 8-Channel 300 µL pipette mounted on?",
    choices=[
        {"display_name": "left", "value": "left"},
        {"display_name": "right", "value": "right"},
    ],
    default="left"
    )

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    # load labware
    # TO-DO: change labware to match actual labware used
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    drug_plate = protocol.load_labware("greinermasterblock_96_wellplate_2000ul", 5)

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
        drug_plate_metadata = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\drug_plate_metadata_v1.3.csv")
    elif platform == "linux":
        # load the drug layout on drug master plate
        drug_plate_metadata = pd.read_csv("/data/user_storage/apricot_data/drug_plate_metadata_v1.3.csv")


    # load drugs into 96-well plate
    for i, well in drug_plate_metadata.iterrows():
        well = drug_plate[well.row + str(well.col)]
        well.load_liquid(liquid=drugs, volume=5)

    # load media into reservoir
    reservoir['A1'].load_liquid(liquid=media, volume=13000)
    reservoir['A2'].load_liquid(liquid=media, volume=13000)

    # initialize pipette
    pipette = protocol.load_instrument("p300_multi_gen2", "left",
                                       tip_racks=[tips])

    # set well clearance of pipettes
    pipette.well_bottom_clearance.aspirate = 1.5
    pipette.well_bottom_clearance.dispense = 1.5

    dest_wells = ["A" + str(col) for col in drug_plate_metadata.col.unique()]
    destinations = [drug_plate[well] for well in dest_wells]

    source_well = "A1"
    pipette.transfer(volume=297,
                          source=reservoir[source_well],
                          dest=destinations[0:5],
                          mix_after=(3, 200),
                          new_tip='always')
    
    source_well = "A2"
    pipette.transfer(volume=297,
                          source=reservoir[source_well],
                          dest=destinations[5:],
                          mix_after=(3, 200),
                          new_tip='always')

