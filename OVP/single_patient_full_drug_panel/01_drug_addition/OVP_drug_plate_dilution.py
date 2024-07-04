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
    variable_name="right_pipette",
    display_name="right pipette",
    description="Pipette that is mounted on the right holder. This pipette is not used in this protocol, but you can change it here in case a different pipette is currently on the OT-2.",
    choices=[
        {"display_name": "1-Channel 20 µL", "value": "p20_single_gen2"},
        {"display_name": "8-Channel 20 µL", "value": "p20_multi_gen2"},
        {"display_name": "1-Channel 300 µL", "value": "p300_single_gen2"},
        {"display_name": "8-Channel 300 µL", "value": "p300_multi_gen2"},
        {"display_name": "1-Channel 1000 µL", "value": "p1000_single_gen2"},
    ],
    default="p20_single_gen2"
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
    left_pipette = protocol.load_instrument("p300_multi_gen2", "left",
                                            tip_racks=[tips])
    right_pipette = protocol.load_instrument(protocol.params.right_pipette, "right",
                                            tip_racks=[tips])

    # set well clearance of pipettes
    left_pipette.well_bottom_clearance.aspirate = 1.5
    left_pipette.well_bottom_clearance.dispense = 1.5
    right_pipette.well_bottom_clearance.aspirate = 1.5
    right_pipette.well_bottom_clearance.dispense = 1.5

    dest_wells = ["A" + str(col) for col in drug_plate_metadata.col.unique()]
    destinations = [drug_plate[well] for well in dest_wells]

    source_well = "A1"
    left_pipette.transfer(volume=297,
                          source=reservoir[source_well],
                          dest=destinations[0:5],
                          mix_after=(3, 200),
                          new_tip='always')
    
    source_well = "A2"
    left_pipette.transfer(volume=297,
                          source=reservoir[source_well],
                          dest=destinations[5:],
                          mix_after=(3, 200),
                          new_tip='always')

