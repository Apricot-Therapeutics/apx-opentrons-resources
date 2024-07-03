from opentrons import protocol_api
import pandas as pd
from sys import platform
import numpy as np
from opentrons.protocol_api import Well
from typing import Optional
import itertools

# helper function to distribute with more flexibility
def distribute(volume: int,
               source: Well,
               dest: list[Well],
               aspirate_delay: float,
               dispense_delay: float,
               residual_volume: int,
               pipette,
               protocol: protocol_api.ProtocolContext,
               residual_dispense_height_from_bottom: int,
               touch_tip: bool,
               touch_tip_radius: float,
               touch_tip_v_offset: float,
               residual_dispense_location: Optional[Well] = None,
               n_mix: Optional[int] = None,
               aspirate_rate: float = 1.0,
               dispense_rate: float = 1.0,):
    
    # based on the volume, calculate how often can be pipetted
    n_pipetting_steps = np.floor((300 - residual_volume)/volume) # TO-DO: max volume of pipette
    
    # chunk up the destinations
    chunked_dest = np.array_split(dest, np.ceil(len(dest)/n_pipetting_steps))

    for sub_list in chunked_dest:
        pipette.pick_up_tip()

        # mix if required
        if n_mix is not None:
            pipette.mix(
                repetitions=n_mix,
                volume=len(sub_list)*volume + residual_volume, 
                location=source,
                rate=aspirate_rate
                )     
        # iterate over destination sublists and aspirate
        pipette.aspirate(
            volume=len(sub_list)*volume + residual_volume, 
            location=source,
            rate=aspirate_rate
        )

        # short delay
        protocol.delay(seconds=aspirate_delay)
        # iterate over each destination and dispense 5 ul
        for destination in sub_list:
            pipette.dispense(
                volume=volume,
                location=destination,
                rate=dispense_rate
            )
            # short delay
            protocol.delay(seconds=dispense_delay)

            if touch_tip:
                pipette.touch_tip(radius=touch_tip_radius,
                                  v_offset=touch_tip_v_offset)

        if residual_dispense_location is not None:
            pipette.dispense(location=residual_dispense_location.bottom(z=residual_dispense_height_from_bottom))
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
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
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
        cell_plate_metadata = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\plate_metadata_v1.2.csv")
    elif platform == "linux":
        # load the drug layout on drug master plate and final 384-well plate
        cell_plate_metadata = pd.read_csv("/data/user_storage/apricot_data/plate_metadata_v1.2.csv")

    # for now, only 1 patient
    cell_plate_metadata = cell_plate_metadata.loc[
        cell_plate_metadata["sample"] != "patient_2"]

    # load antibodies into 96-well plate
    for well in antibody_plate.columns()[0]:
        well.load_liquid(liquid=antibodies, volume=650)
    # load samples
    for i, well in cell_plate_metadata.iterrows():
        well = cell_plate[well.row + str(well.col)]
        well.load_liquid(liquid=sample, volume=30)

    # initialize pipette
    left_pipette = protocol.load_instrument("p300_multi_gen2", "left",
                                            tip_racks=[tips])
    right_pipette = protocol.load_instrument("p20_single_gen2", "right",
                                            tip_racks=[tips])

    # set well clearance of pipettes
    left_pipette.well_bottom_clearance.aspirate = 1.0
    left_pipette.well_bottom_clearance.dispense = 3.0
    right_pipette.well_bottom_clearance.aspirate = 1.0
    right_pipette.well_bottom_clearance.dispense = 3.0

    source_well = 'A4'
    dest_wells = [[row + str(col) for col in cell_plate_metadata.col.unique()] for row in ["A", "B"]]
    dest_wells = list(itertools.chain.from_iterable(dest_wells))
    destinations = [cell_plate[well] for well in dest_wells]

    distribute(
        volume=30,
        source=antibody_plate[source_well],
        dest=destinations,
        aspirate_delay=1.0,
        dispense_delay=1.0,
        n_mix=1,
        residual_volume=20,
        pipette=left_pipette,
        protocol=protocol,
        residual_dispense_location=antibody_plate[source_well],
        residual_dispense_height_from_bottom=1,
        dispense_rate=0.4,
        touch_tip=True,
        touch_tip_radius=0.4,
        touch_tip_v_offset=-5
    )