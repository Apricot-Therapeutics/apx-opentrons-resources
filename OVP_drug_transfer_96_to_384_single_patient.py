from opentrons import protocol_api
import pandas as pd

# metadata
metadata = {
    "protocolName": "OVP Drug Transfer to 384-well Cell Plate",
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
    drug_plate = protocol.load_labware("thermoscientific_96_wellplate_1300ul", 5)
    cell_plate = protocol.load_labware("greiner_bio_one_384_well_plate_100ul_reduced_well_size", 6)

    # for local testing
    #drug_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    #cell_plate = protocol.load_labware("corning_384_wellplate_112ul_flat", 3)

    # optional: set liquids
    sample = protocol.define_liquid(name="sample", display_color="#1c03fc",
                                    description="sample to which to add drugs")
    drugs = protocol.define_liquid(name="drugs", display_color="#fcba03",
                                 description="drugs to be transferred")

    # load some metadata we need later

    # load the drug layout on drug master plate and final 384-well plate
    drug_plate_layout = pd.read_csv(
        r"C:\Users\OT-Operator\Documents\OT-2_protocols\Apricot\OVP\metadata\drug_plate_metadata_v1.0.csv")
    cell_plate_layout = pd.read_csv(
        r"C:\Users\OT-Operator\Documents\OT-2_protocols\Apricot\OVP\metadata\plate_metadata_v1.0.csv")

    # for now, only 1 patient
    cell_plate_layout = cell_plate_layout.loc[
        cell_plate_layout["sample"] != "patient_2"]

    # load drugs into 96-well plate
    for i, well in drug_plate_layout.iterrows():
        well = drug_plate[well.row + str(well.col)]
        well.load_liquid(liquid=drugs, volume=1000)

    for i, well in cell_plate_layout.iterrows():
        well = cell_plate[well.row + str(well.col)]
        well.load_liquid(liquid=sample, volume=45)

    # initialize pipette
    left_pipette = protocol.load_instrument("p300_multi_gen2", "left",
                                            tip_racks=[tips])
    right_pipette = protocol.load_instrument("p20_single_gen2", "right",
                                            tip_racks=[tips])

    for i, drug in drug_plate_layout.iterrows():
        # assemble name of source well (opentrons take A1 instead of A01)
        source_well = drug.row + str(drug.col)
        # collect destination wells
        dest_wells = cell_plate_layout.loc[
            cell_plate_layout.condition == drug.condition]
        # put together names for destination wells
        dest_wells = [well.row + str(well.col) for i, well
                      in dest_wells.iterrows()]

        destinations = [cell_plate[well] for well in dest_wells]

        print(f"Distributing {drug.condition} from well {source_well} "
              f"to wells {dest_wells} on 384-well cell plate")

        # distribute from source well to dest wells
        right_pipette.distribute(volume=5,
                                 source=drug_plate[source_well],
                                 dest=destinations,
                                 disposal_volume=5)

