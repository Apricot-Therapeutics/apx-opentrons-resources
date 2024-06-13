from opentrons import protocol_api
import pandas as pd
from sys import platform

# metadata
metadata = {
    "protocolName": "OVP Prepare Drug Plates from Master Plate",
    "description": """This protocol is used to prepare drug plates to be frozen
     from a pre-prepared 96-well drug plate containing drugs at 2000x and 1000x
     concentrations.""",
    "author": "Adrian Tschan"
    }

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.16"}

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    # load labware
    # TO-DO: change labware to match actual labware used
    tips = protocol.load_labware("opentrons_96_filtertiprack_20ul", 7)
    drug_master_plate = protocol.load_labware("greinermasterblock_96_wellplate_2000ul", 8)
    drug_plate = protocol.load_labware("greinermasterblock_96_wellplate_2000ul", 1)

    # for local testing
    #drug_master_plate = protocol.load_labware(
    #    "nest_96_wellplate_200ul_flat", 2)
    #drug_plate = protocol.load_labware(
    #    "nest_96_wellplate_200ul_flat", 3)


    # optional: set liquids
    drugs = protocol.define_liquid(name="drugs", display_color="#fcba03",
                                 description="drugs to be transferred")

    # load some metadata we need later
    if platform == "win32":
        # load the drug layout on drug master plate
        drug_plate_layout = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\drug_plate_metadata_v1.3.csv")
        #drug_plate_layout = pd.read_csv(
        #    r"K:\projects\OV_Precision\documents\plate_layout\drug_plate_metadata_v1.1.csv")
    elif platform == "linux":
        # load the drug layout on drug master plate
        drug_plate_layout = pd.read_csv("/data/user_storage/apricot_data/drug_plate_metadata_v1.3.csv")


    # load drugs into 96-well plate
    for i, well in drug_plate_layout.iterrows():
        well = drug_master_plate[well.row + str(well.col)]
        well.load_liquid(liquid=drugs, volume=1000)

    # initialize pipette
    left_pipette = protocol.load_instrument("p20_multi_gen2", "left",
                                            tip_racks=[tips])
    right_pipette = protocol.load_instrument("p20_single_gen2", "right",
                                            tip_racks=[tips])

# set well clearance of pipettes
    left_pipette.well_bottom_clearance.aspirate = 0.5
    left_pipette.well_bottom_clearance.dispense = 0.5
    right_pipette.well_bottom_clearance.aspirate = 0.5
    right_pipette.well_bottom_clearance.dispense = 0.5

    left_pipette.pick_up_tip()

    # get source and destination wells
    source_well = "A1"

    # pre-wet
    left_pipette.aspirate(volume=20,
                        location=drug_master_plate[source_well],
                        rate=0.5)
    left_pipette.dispense(volume=20,
                            location=drug_master_plate[source_well],
                            rate=0.5)

    # distribute from source well to dest wells
    left_pipette.aspirate(volume=20,
                        location=drug_master_plate[source_well],
                        rate=0.5)
    
    protocol.delay(seconds=1.0)

    left_pipette.touch_tip(radius=0.4,
                            v_offset=-25)

    for i in range(1, 7):
        destination_well = "A" + str(i)
        left_pipette.dispense(volume=3,
                                location=drug_plate[destination_well],
                                rate=0.5)
        protocol.delay(seconds=1.0)

        left_pipette.touch_tip(radius=0.4,
                                v_offset=-25)
        
    # some weird behaviour with blow_out: when blowing out into the liquid, the next round
    # does not aspirate enough. Possibly because of an airbubble that gets deposited.
    # It's fine however if the blowout does not go into the liquid.   
    
    #left_pipette.blow_out(location=drug_master_plate['A1'].bottom(z=0.5))
    #left_pipette.touch_tip(radius=0.4,
    #                       v_offset=-25)
    #left_pipette.move_to(drug_master_plate["A1"].top(z=30))
                              

    left_pipette.drop_tip()


