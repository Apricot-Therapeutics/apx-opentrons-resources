from opentrons import protocol_api
from opentrons.protocol_api import Well
import pandas as pd
from sys import platform
from typing import Optional
import numpy as np
import itertools
import string

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
    "protocolName": "OVP Cell Seeding",
    "description": """This protocol is used to seed patient sample cells 
    and OVCAR3 cells on a 384-well plate""",
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

    parameters.add_str(
    variable_name="pipette_position_20ul",
    display_name="p20 single-channel position",
    description="Which mount is the single-channel 20 µL pipette mounted on?",
    choices=[
        {"display_name": "left", "value": "left"},
        {"display_name": "right", "value": "right"},
    ],
    default="right"
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

    parameters.add_int(
        variable_name="sample_1_col",
        display_name="Patient 1 reservoir column",
        description="The reservoir column containing cells from patient 1",
        default=1,
        minimum=1,
        maximum=12,
    )

    parameters.add_int(
        variable_name="cell_line_col",
        display_name="Cell line reservoir column",
        description="The reservoir column containing OVCAR3 cells",
        default=3,
        minimum=1,
        maximum=12,
    )

    parameters.add_int(
        variable_name="sample_2_col",
        display_name="Patient 2 reservoir column",
        description="The reservoir column containing cells from patient 2. Only used if two patients are processed.",
        default=5,
        minimum=1,
        maximum=12,
    )

    parameters.add_int(
        variable_name="rpmi_col",
        display_name="RPMI reservoir column",
        description="The reservoir column containing RPMI to fill up wells adjacent to sample wells.",
        default=7,
        minimum=1,
        maximum=12,
    )

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    # load labware
    # TO-DO: change labware to match actual labware used
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tips_20ul = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    cell_plate = protocol.load_labware("greiner_bio_one_384_well_plate_100ul_reduced_well_size", 6)

    # optional: set liquids
    patient_1 = protocol.define_liquid(name="Patient 1 sample", display_color="#1c03fc",
                                    description="Cells from patient 1")
    patient_2 = protocol.define_liquid(name="Patient 2 sample", display_color="#1c04fc",
                                    description="Cells from patient 2")
    ovcar3 = protocol.define_liquid(name="OVCAR3 sample", display_color="#1c05fc",
                                    description="OVCAR3 cells")
    rpmi = protocol.define_liquid(name="RPMI medium", display_color="#1c06fc",
                                    description="RPMI medium to fill wells adjacent to sample wells")

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

    # load media into reservoir
    reservoir['A' + str(protocol.params.sample_1_col)].load_liquid(liquid=patient_1, volume=5000)
    reservoir['A' + str(protocol.params.cell_line_col)].load_liquid(liquid=ovcar3, volume=5000)
    reservoir['A' + str(protocol.params.rpmi_col)].load_liquid(liquid=rpmi, volume=5000)

    # if second patient sample is provided, include it:
    if protocol.params.process_full_plate:
        reservoir['A' + str(protocol.params.sample_2_col)].load_liquid(liquid=patient_2, volume=5000)

    # initialize pipette
    pipette = protocol.load_instrument("p300_multi_gen2", 
                                       protocol.params.pipette_position,
                                       tip_racks=[tips])
    
    pipette_20ul = protocol.load_instrument("p20_single_gen2", 
                                       protocol.params.pipette_position_20ul,
                                       tip_racks=[tips_20ul])

    # set well clearance of pipettes
    pipette.well_bottom_clearance.aspirate = 1
    pipette.well_bottom_clearance.dispense = 2
    pipette_20ul.well_bottom_clearance.aspirate = 1
    pipette_20ul.well_bottom_clearance.dispense = 2

    for sample_type in cell_plate_metadata["sample"].unique():

        current_metadata = cell_plate_metadata.loc[cell_plate_metadata["sample"] == sample_type]

        dest_wells = [[row + str(col) for col in current_metadata.col.unique()] for row in ["A", "B"]]
        dest_wells = list(itertools.chain.from_iterable(dest_wells))
        destinations = [cell_plate[well] for well in dest_wells]

        if sample_type == "patient_1":
            source_well = 'A' + str(protocol.params.sample_1_col)
        elif sample_type == "patient_2":
            source_well = 'A' + str(protocol.params.sample_2_col)
        elif sample_type == "OVCAR3":
            source_well = 'A' + str(protocol.params.cell_line_col)

        pipette.pick_up_tip()

        distribute(
            volume=45,
            source=reservoir[source_well],
            dest=destinations,
            aspirate_delay=1.0,
            dispense_delay=0,
            residual_volume=20,
            n_mix=3,
            pipette=pipette,
            protocol=protocol,
            residual_dispense_location=reservoir[source_well],
            residual_dispense_height_from_bottom=3.5,
            touch_tip=True,
            touch_tip_radius=0.4,
            touch_tip_v_offset=-5,
            ignore_tips=True
            )
        
        pipette.drop_tip()

    # after seeding is done, distribute RPMI to wells adjacent to wells containing media
    if (protocol.params.process_full_plate == True) & (protocol.params.exclude_experimental_drugs == False):
        destinations_rows = [[row + str(col) for col in range(2, 23)] for row in ["B", "O"]]
        destinations_cols = [[row + str(col) for row in ["A", "B"]] for col in ["2", "22"]]
        destinations_rows = list(itertools.chain.from_iterable(destinations_rows))
        destinations_cols = list(itertools.chain.from_iterable(destinations_cols))

    elif (protocol.params.process_full_plate == True) & (protocol.params.exclude_experimental_drugs == True):
        destinations_rows = [[row + str(col) for col in range(2, 23)] for row in ["B", "O"]]
        destinations_cols = [[row + str(col) for row in ["A", "B"]] for col in ["2", "9", "11", "19"]]
        destinations_rows = list(itertools.chain.from_iterable(destinations_rows))
        destinations_cols = list(itertools.chain.from_iterable(destinations_cols))

    elif (protocol.params.process_full_plate == False) & (protocol.params.exclude_experimental_drugs == False):
        destinations_rows = [[row + str(col) for col in range(2, 14)] for row in ["B", "O"]]
        destinations_cols = [[row + str(col) for row in ["A", "B"]] for col in ["2", "13"]]
        destinations_rows = list(itertools.chain.from_iterable(destinations_rows))
        destinations_cols = list(itertools.chain.from_iterable(destinations_cols))

    elif (protocol.params.process_full_plate == True) & (protocol.params.exclude_experimental_drugs == True):
        destinations_rows = [[row + str(col) for col in range(2, 14)] for row in ["B", "O"]]
        destinations_cols = [[row + str(col) for row in ["A", "B"]] for col in ["2", "9", "11", "13"]]
        destinations_rows = list(itertools.chain.from_iterable(destinations_rows))
        destinations_cols = list(itertools.chain.from_iterable(destinations_cols))

    destinations_rows = [cell_plate[well] for well in destinations_rows]
    destinations_cols = [cell_plate[well] for well in destinations_cols]

    source_well = 'A' + str(protocol.params.rpmi_col)

    # pipette columns

    pipette.pick_up_tip()

    distribute(
        volume=40,
        source=reservoir[source_well],
        dest=destinations_cols,
        dispense_delay=0.25,
        residual_volume=20,
        pipette=pipette,
        protocol=protocol,
        touch_tip=True,
        touch_tip_radius=0.4,
        touch_tip_v_offset=-5,
        ignore_tips=True
        )
        
    pipette.drop_tip()

    pipette_20ul.pick_up_tip()

    for dest in destinations_rows:

        for i in range(0, 2):
    
            pipette_20ul.aspirate(
                volume=20,
                location=reservoir[source_well],
                rate=5.0,
            )

            pipette_20ul.dispense(
                volume=20,
                location=dest,
                rate=5.0,
            )

            protocol.delay(seconds=0.25)

            pipette_20ul.touch_tip(radius=0.4,
                                v_offset=-5)
    
    pipette_20ul.drop_tip()


    
    


