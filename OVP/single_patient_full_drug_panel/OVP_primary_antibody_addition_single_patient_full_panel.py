from opentrons import protocol_api
import pandas as pd
from sys import platform
import numpy as np
from opentrons.protocol_api import Well
from typing import Optional

# helper function to distribute with more flexibility
def distribute(volume: int,
               source: Well,
               dest: list[Well],
               delay: int,
               residual_volume: int,
               pipette,
               protocol: protocol_api.ProtocolContext,
               blow_out_height_from_bottom: int,
               blow_out_location: Optional[Well] = None,):
    
    # based on the volume, calculate how often can be pipetted
    n_pipetting_steps = np.floor(20/(volume - residual_volume)) # TO-DO: max volume of pipette
    
    # chunk up the destinations
    chunked_dest = np.array_split(dest, np.ceil(len(dest)/n_pipetting_steps))

    for sub_list in chunked_dest:
        # iterate over destination sublists and aspirate
        pipette.pick_up_tip()     
        pipette.aspirate(
            volume=len(sub_list)*volume + residual_volume, 
            location=source,
        )
        # iterate over each destination and dispense 5 ul
        for destination in sub_list:
            pipette.dispense(
                volume=volume,
                location=destination,
            )
            # short delay
            protocol.delay(seconds=delay)

        if blow_out_location is not None:
            pipette.blow_out(location=blow_out_location.bottom(z=blow_out_height_from_bottom))
        # drop tip
        pipette.drop_tip()

# metadata
metadata = {
    "protocolName": "OVP Primary Antibody addition (single patient)",
    "description": """This protocol is used to transfer drugs from a
     pre-prepared 96-well drug plate to a 384 well plate containing patient
     cells (in 45 ul of media) in a randomized layout.""",
    "author": "Adrian Tschan"
    }

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.16"}

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    # load labware
    # TO-DO: change labware to match actual labware used
    tips = protocol.load_labware("opentrons_96_filtertiprack_20ul", 1)
    antibody_plate = protocol.load_labware("greinermasterblock_96_wellplate_2000ul", 5)
    cell_plate = protocol.load_labware("greiner_bio_one_384_well_plate_100ul_reduced_well_size", 6)

    # for local testing
    #antibody_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    #cell_plate = protocol.load_labware("corning_384_wellplate_112ul_flat", 3)

    # optional: set liquids
    sample = protocol.define_liquid(name="sample", display_color="#1c03fc",
                                    description="sample to which to primary antibodies")
    antibodies = protocol.define_liquid(name="primary_antibodies", display_color="#fcba03",
                                 description="primary antibodies")

    # load some metadata we need later
    if platform == "win32":
        # load the drug layout on drug master plate and final 384-well plate
        cell_plate_metadata = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\Apricot\OVP\metadata\plate_metadata_v1.2.csv")
    elif platform == "linux":
        # load the drug layout on drug master plate and final 384-well plate
        cell_plate_metadata = pd.read_csv("/data/user_storage/apricot_data/plate_metadata_v1.2.csv")

    # for now, only 1 patient
    cell_plate_metadata = cell_plate_metadata.loc[
        cell_plate_metadata["sample"] != "patient_2"]

    # load antibodies into 96-well plate
    for well in antibody_plate.columns()[0]:
        well.load_liquid(liquid=antibodies, volume=500)
    # load samples
    for i, well in cell_plate_metadata.iterrows():
        well = cell_plate[well.row + str(well.col)]
        well.load_liquid(liquid=sample, volume=20)

    # initialize pipette
    left_pipette = protocol.load_instrument("p20_multi_gen2", "left",
                                            tip_racks=[tips])
    right_pipette = protocol.load_instrument("p20_single_gen2", "right",
                                            tip_racks=[tips])

    # set well clearance of pipettes
    left_pipette.well_bottom_clearance.aspirate = 0.5
    left_pipette.well_bottom_clearance.dispense = 1.5
    right_pipette.well_bottom_clearance.aspirate = 0.5
    right_pipette.well_bottom_clearance.dispense = 1.5

    source_well = 'A1'
    dest_wells = ['A' + str(col) for col in cell_plate_metadata.col.unique()]
    destinations = [cell_plate[well] for well in dest_wells]

    distribute(
        volume=5,
        source=antibody_plate[source_well],
        dest=destinations,
        delay=1.0,
        residual_volume=2.0,
        pipette=left_pipette,
        protocol=protocol,
        blow_out_location=antibody_plate[source_well],
        blow_out_height_from_bottom=1,
    )