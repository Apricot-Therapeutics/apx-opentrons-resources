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
    tips = protocol.load_labware("opentrons_96_filtertiprack_20ul", 1)
    #drug_master_plate = protocol.load_labware("thermoscientific_96_wellplate_1300ul", 2)
    #drug_plates = [protocol.load_labware("thermoscientific_96_wellplate_1300ul", i)
    #               for i in range(3, 12)]

    # for local testing
    drug_master_plate = protocol.load_labware(
        "nest_96_wellplate_200ul_flat", 2)
    drug_plate = protocol.load_labware(
        "nest_96_wellplate_200ul_flat", 3)


    # optional: set liquids
    drugs = protocol.define_liquid(name="drugs", display_color="#fcba03",
                                 description="drugs to be transferred")

    # load some metadata we need later
    if platform == "win32":
        # load the drug layout on drug master plate
        #drug_plate_layout = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\Apricot\OVP\single_patient_plate\drug_plate_metadata_v1.0.csv")
        drug_plate_layout = pd.read_csv(
            r"K:\projects\OV_Precision\documents\plate_layout\drug_plate_metadata_v1.1.csv")
    elif platform == "linux":
        # load the drug layout on drug master plate
        drug_plate_layout = pd.read_csv("/data/user_storage/apricot_data/drug_plate_metadata_v1.0.csv")


    # load drugs into 96-well plate
    for i, well in drug_plate_layout.iterrows():
        well = drug_master_plate[well.row + str(well.col)]
        well.load_liquid(liquid=drugs, volume=1000)

    # initialize pipette
    left_pipette = protocol.load_instrument("p20_multi_gen2", "left",
                                            tip_racks=[tips])
    right_pipette = protocol.load_instrument("p1000_single_gen2", "right",
                                            tip_racks=[tips])

    # set well clearance of pipettes
    left_pipette.well_bottom_clearance.aspirate = 1.5
    left_pipette.well_bottom_clearance.dispense = 1.5
    right_pipette.well_bottom_clearance.aspirate = 1.5
    right_pipette.well_bottom_clearance.dispense = 1.5

    left_pipette.pick_up_tip()

    for i in range(0, 20):

        # get source and destination wells
        source_well = "A1"
        destination_well = source_well

        # distribute from source well to dest wells
        left_pipette.aspirate(volume=20,
                              location=drug_master_plate[source_well],
                              rate=0.5)

        left_pipette.touch_tip(radius=0.75,
                               v_offset=-2)

        for i in range(0, 3):
            left_pipette.dispense(volume=5,
                                  location=drug_plate[destination_well],
                                  rate=0.5)

            left_pipette.touch_tip(radius=0.75,
                                   v_offset=-2)

        left_pipette.blow_out(location=drug_master_plate[destination_well].bottom())

    left_pipette.drop_tip()


