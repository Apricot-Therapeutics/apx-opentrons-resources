from opentrons import protocol_api

# metadata
metadata = {
    "protocolName": "Serial Dilution Tutorial",
    "description": """This protocol is the outcome of following the
                   Python Protocol API Tutorial located at
                   https://docs.opentrons.com/v2/tutorial.html. It takes a
                   solution and progressively dilutes it by transferring it
                   stepwise across a plate.""",
    "author": "New API User"
    }

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.16"}

# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)

    # optional: set liquids
    diluent = protocol.define_liquid(name="diluent", display_color="#1c03fc",
                                     description="A liquid to dilute the dye")
    dye = protocol.define_liquid(name="dye", display_color="#fcba03",
                                 description="A liquid to be diluted")
    reservoir['A1'].load_liquid(liquid=dye, volume=20000)
    reservoir['A2'].load_liquid(liquid=diluent, volume=20000)

    # initialize pipette
    left_pipette = protocol.load_instrument("p300_single", "left",
                                            tip_racks=[tips])

    # transfer diluent from reservoir to plate
    left_pipette.transfer(100, reservoir["A1"], plate.wells())

    # serial dilution
    for i in range(8):
        row = plate.rows()[i]
        left_pipette.transfer(100, reservoir["A2"], row[0], mix_after=(3, 50))
        left_pipette.transfer(100, row[:11], row[1:], mix_after=(3, 50))