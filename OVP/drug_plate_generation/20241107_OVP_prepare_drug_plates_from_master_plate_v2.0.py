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
    drug_plates = [protocol.load_labware("greinermasterblock_96_wellplate_2000ul", i)
                   for i in range(1, 7)]

    # for local testing
    #drug_master_plate = protocol.load_labware(
    #    "nest_96_wellplate_200ul_flat", 8)
    #drug_plates = [protocol.load_labware("nest_96_wellplate_200ul_flat", i)
    #               for i in range(1, 7)]


    # optional: set liquids
    drugs = protocol.define_liquid(name="drugs", display_color="#fcba03",
                                 description="drugs to be transferred")

    # load some metadata we need later
    if platform == "win32":
        # load the drug layout on drug master plate
        drug_plate_layout = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\drug_plate_metadata_v2.0.csv")
        #drug_plate_layout = pd.read_csv(
        #    r"K:\projects\OV_Precision\documents\plate_layout\drug_plate_metadata_v1.1.csv")
    elif platform == "linux":
        # load the drug layout on drug master plate
        drug_plate_layout = pd.read_csv("/data/user_storage/apricot_data/OVP/drug_plate_metadata_v2.0.csv")


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

    # antibody drugs in columns 6 and 12 (manually pipetted)
    drug_plate_layout = drug_plate_layout.loc[~drug_plate_layout["col"].isin([6, 12])]

    for col in drug_plate_layout["col"].unique():
        # pick up a column of tips
        left_pipette.pick_up_tip()
        # get source and destination wells
        source_well = "A" + str(col)
        destination_well = source_well

        # pre-wet
        left_pipette.aspirate(volume=20,
                            location=drug_master_plate[source_well],
                            rate=0.5)
        left_pipette.dispense(volume=20,
                              location=drug_master_plate[source_well],
                              rate=0.5)

        # aspirate 20 ul from source to distribute
        left_pipette.aspirate(volume=20,
                            location=drug_master_plate[source_well],
                            rate=0.5)
        # short delay to allow viscous liquid to settle
        protocol.delay(seconds=1.0)
        # tip touch with low radius and -25 mm offset from top of well
        left_pipette.touch_tip(radius=0.4,
                                v_offset=-25)

        for drug_plate in drug_plates:
            left_pipette.dispense(volume=3,
                                  location=drug_plate[destination_well],
                                  rate=0.5)
            # short delay to allow viscous liquid to settle
            protocol.delay(seconds=1.0)
            # tip touch with low radius and -25 mm offset from top of well
            left_pipette.touch_tip(radius=0.4,
                                    v_offset=-25)
            
        # some weird behaviour with blow_out: when blowing out into the liquid, the next round
        # does not aspirate enough. Possibly because of an airbubble that gets deposited.
        # It's fine however if the blowout does not go into the liquid. For now,
        # we skip the blowout.
        
        #left_pipette.blow_out(location=drug_master_plate['A1'])
        #left_pipette.touch_tip(radius=0.5,
        #                            v_offset=-25)
                              
        # drop the tips with remaining 2 ul into trash
        left_pipette.drop_tip()


