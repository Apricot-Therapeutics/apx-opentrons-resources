from opentrons import protocol_api
from opentrons.protocol_api import Well
import pandas as pd
from sys import platform
from typing import Optional
import numpy as np
import itertools

# helper function to distribute with more flexibility
def distribute(volume: int,
               source: Well,
               dest: list[Well],
               pipette,
               protocol: protocol_api.ProtocolContext,
               aspirate_delay: float = 0,
               dispense_delay: float = 0,
               residual_volume: int = 0,
               residual_dispense_height_from_bottom: Optional[int] = None,
               touch_tip_radius: Optional[float] = None,
               touch_tip_v_offset: Optional[float] = None,
               touch_tip: bool = False,
               residual_dispense_location: Optional[Well] = None,
               n_mix: Optional[int] = None,
               aspirate_rate: float = 1.0,
               dispense_rate: float = 1.0,
               reuse_tips=False,
               ignore_tips=False,
               pre_wet_tips=False,):
    
    # based on the volume, calculate how often can be pipetted
    n_pipetting_steps = np.floor((300 - residual_volume)/volume) # TO-DO: max volume of pipette
    
    # chunk up the destinations
    chunked_dest = np.array_split(dest, np.ceil(len(dest)/n_pipetting_steps))

    for i, sub_list in enumerate(chunked_dest):
        if ignore_tips == False:
            if reuse_tips == False:
                pipette.pick_up_tip()
            if (reuse_tips == True) & (i == 0):
                pipette.pick_up_tip()

        # pre-wet tip if required:
        if pre_wet_tips:
            pipette.aspirate(volume=300,
                             location=source)
            pipette.dispense(volume=300,
                             location=source)

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
        if ignore_tips == False:
            if (reuse_tips == False) or (i == (len(chunked_dest) -1)):
                pipette.drop_tip()

# metadata
metadata = {
    "protocolName": "OVP PFA Fixation",
    "description": """This protocol is used to add a 8% PFA solution
    to a 384-well plate containing patient samples.""",
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

    parameters.add_bool(
    variable_name="exclude_experimental_drugs",
    display_name="Exclude experimental drugs",
    description="Turn on if the experimental drug set should be excluded.",
    default=False,
    )

    parameters.add_bool(
    variable_name="process_full_plate",
    display_name="Process two patient samples",
    description="Turn on if there are two patient samples on the plate (full plate).",
    default=False,
    )

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    protocol.pause(msg='IMPORTANT: Has the cell plate been aspirated to 40 ul on the washer-dispenser? If no, do so before resuming the protocol.')

    # load labware
    # TO-DO: change labware to match actual labware used
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    cell_plate = protocol.load_labware("greiner_bio_one_384_well_plate_100ul_reduced_well_size", 6)

    # optional: set liquids
    sample = protocol.define_liquid(name="sample", display_color="#1c03fc",
                                    description="wells that will contain sample")
    PFA = protocol.define_liquid(name="8% PFA in PBS", display_color="#1c03fc",
                                 description="fixation solution")

    # load some metadata we need later
    if platform == "win32":
        # load the drug layout on drug master plate and final 384-well plate
        cell_plate_metadata = pd.read_csv(r"C:\Users\OT-Operator\Documents\OT-2_protocols\APx_opentrons_resources\OVP\metadata\plate_metadata_v1.2.csv")

    elif platform == "linux":
        # load the drug layout on drug master plate and final 384-well plate
        cell_plate_metadata = pd.read_csv("/data/user_storage/apricot_data/plate_metadata_v1.2.csv")

    # process one or two patient samples
    if protocol.params.process_full_plate == False:
        cell_plate_metadata = cell_plate_metadata.loc[
            cell_plate_metadata["sample"] != "patient_2"]
    
    # include or exclude experimental drugs
    if protocol.params.exclude_experimental_drugs:
        cell_plate_metadata = cell_plate_metadata.loc[cell_plate_metadata.drug_panel == "standard"]

    for i, well in cell_plate_metadata.iterrows():
        well = cell_plate[well.row + str(well.col)]
        well.load_liquid(liquid=sample, volume=40)

    # load media into reservoir
    reservoir['A1'].load_liquid(liquid=PFA, volume=7000)

    # initialize pipette
    pipette = protocol.load_instrument("p300_multi_gen2", "left",
                                       tip_racks=[tips])

    # set well clearance of pipettes
    pipette.well_bottom_clearance.aspirate = 1
    pipette.well_bottom_clearance.dispense = 4

    dest_wells = [[row + str(col) for col in cell_plate_metadata.col.unique()] for row in ["A", "B"]]
    dest_wells = list(itertools.chain.from_iterable(dest_wells))
    destinations = [cell_plate[well] for well in dest_wells]

    source_well = "A1"

    distribute(
        volume=40,
        source=reservoir[source_well],
        dest=destinations,
        aspirate_delay=1.0,
        dispense_delay=1.0,
        dispense_rate=0.5,
        residual_volume=20,
        pipette=pipette,
        protocol=protocol,
        touch_tip=True,
        touch_tip_radius=0.4,
        touch_tip_v_offset=-5,
        reuse_tips=True,
        pre_wet_tips=True,
        residual_dispense_location=reservoir[source_well],
        residual_dispense_height_from_bottom=2.5,
        )
        
    


