import zlib
from pathlib import Path
import numpy

import cProfile
    


class BitReader:
    def __init__(self, data:bytes):
        self.data = data
        self.bit_pos = 0
        self.length = len(data)*8

    def read_bool(self) -> bool:
        pos = self.bit_pos
        self.bit_pos = pos + 1
        return (self.data[pos >> 3] >> (7 - (pos & 7))) & 1

    def read_uint32(self) -> int:
        bit_pos = self.bit_pos
        byte_pos = bit_pos >> 3
        offset = bit_pos & 7

        if offset == 0:
            result = (
                (self.data[byte_pos] << 24)
                | (self.data[byte_pos + 1] << 16)
                | (self.data[byte_pos + 2] << 8)
                | self.data[byte_pos + 3]
            )

        else:
            value = (
                (self.data[byte_pos] << 32)
                | (self.data[byte_pos + 1] << 24)
                | (self.data[byte_pos + 2] << 16)
                | (self.data[byte_pos + 3] << 8)
                | self.data[byte_pos + 4]
            )

            result = (value >> (8 - offset)) & 0xFFFFFFFF

        self.bit_pos += 32
        return result

    def read_bits(self, count: int) -> int:
        bit_pos = self.bit_pos

        if bit_pos + count > self.length:
            return 0


        bit_offset = bit_pos & 7
        byte_pos = bit_pos >> 3

        total_bits = bit_offset + count
        byte_count = (total_bits + 7) >> 3

        value = int.from_bytes(
            self.data[byte_pos:byte_pos + byte_count],
            "big"
        )

        # Remove bits after the requested data
        value >>= byte_count * 8 - total_bits

        # Remove bits before the requested data
        value &= (1 << count) - 1

        self.bit_pos += count

        return value

    def read_bytes(self, count:int) -> bytearray:
        result = bytearray()
        for i in range(count):
            result.append(self.read_bits(8))
        return result

    def skip_bits(self, count: int):
        self.bit_pos+=count

    def read_string(self) -> str:
        string_len = self.read_bits(16)
        return self.read_bytes(string_len).decode()


xor_key = [0x6B, 0x10, 0xDE, 0x3C, 0x44, 0x4B, 0xD1, 0x46, 0xA0, 0x10, 0x52, 0xC1, 0xB2, 0x31, 0xD3, 0x6A, 0xFB, 0xAC, 0x11, 0xDE, 0x06, 0x68, 0x08, 0x78, 0x8C, 0xD5, 0xB3, 0xF9, 0x6A, 0x40, 0xD6, 0x13, 0x0C, 0xAE, 0x9D, 0xC5, 0xD4, 0x6B, 0x54, 0x72, 0xFC, 0x57, 0x5D, 0x1A, 0x06, 0x73, 0xC2, 0x51, 0x4B, 0xB0, 0xC9, 0x8C, 0x78, 0x04, 0x11, 0x7A, 0xEF, 0x74, 0x3E, 0x46, 0x39, 0xA0, 0xC7, 0xA6]
key = numpy.array(xor_key, dtype=numpy.uint8)

def read_replay_file(file_bytes: bytes) -> dict:
    decompressed = bytearray(zlib.decompress(file_bytes))

    data = numpy.frombuffer(decompressed, dtype=numpy.uint8)
    repeat_key = numpy.resize(key, data.size)
    data ^= repeat_key

    bit_reader = BitReader(data.tobytes())

    output = {}

    version = bit_reader.read_uint32()

    if version <= 267:
        return None

    output["game_data"] = {"version": version}

    entities = {}
    results = {}
    deaths = {}

    while True:
        section_type = bit_reader.read_bits(4)  
        #print(section_type)
        if section_type == 3:
            header = read_header(bit_reader)
            output["game_data"]["isOnline"] = header["isOnline"]
            if "playlistName" in header.keys():
                output["game_data"]["playlistName"] = header["playlistName"]
        elif section_type == 4:
            player_data = read_player_data(bit_reader, version)
            entities = player_data["entities"]
    
        elif section_type == 6:
            r = read_results(bit_reader)
            if r.keys(): results = r

        elif section_type == 1:
            #print(bit_reader.bit_pos == br2.bit_pos)
            read_inputs(bit_reader)
            #print(bit_reader.bit_pos == br2.bit_pos)

        elif section_type == 5 or section_type == 7:
            deaths = read_faces(bit_reader, section_type == 5)

        elif section_type == 2:
            break
        else:
            print("unhandled type:" + str(section_type))
            break


    output["players"] = {}
    for id in entities:
        output["players"][entities[id]["playerName"]] = {"legends":entities[id]["legends"], "placement":-1, "deaths": -1}
        if "playerID" in entities[id].keys():
            output["players"][entities[id]["playerName"]]["playerID"] = entities[id]["playerID"]
        if id in deaths.keys():
            output["players"][entities[id]["playerName"]]["deaths"] = deaths[id]
        if results:
            output["players"][entities[id]["playerName"]]["placement"] = results[id]



    return output



def read_header(bit_reader: BitReader) -> dict:
    output = {}
    bit_reader.bit_pos+=32
    output["playlistID"] = bit_reader.read_uint32()
    if output["playlistID"] != 0:
        output["playlistName"] = bit_reader.read_string()
    output["isOnline"] = bit_reader.read_bool()

    return output

def read_player_data(bit_reader: BitReader, version: int) -> dict:
    output = {}
    #game settings
    bit_reader.bit_pos+=480
    
    output["levelID"] = bit_reader.read_uint32()
    hero_count = bit_reader.read_bits(16)
    output["heroCount"] = hero_count
    output["entities"] = {}
    while bit_reader.read_bool():
        entity_id = bit_reader.read_uint32()
        output["entities"]
        if version > 267:
            player_id = bit_reader.read_uint32()
            player_name = bit_reader.read_string()
            output["entities"][entity_id] = {"playerID": player_id, "playerName": player_name}
        else:
            player_name = bit_reader.read_string()
            output["entities"][entity_id] = {"playerName": player_name}

        #player creation
        bit_reader.bit_pos+=416
        if version >= 246:
            #companion
            bit_reader.bit_pos+=32
        if version >= 256:
            #trail
            bit_reader.bit_pos+=32
        while bit_reader.read_bool(): bit_reader.bit_pos+=32
        bit_reader.bit_pos+=80

        legends = []
        
        for i in range(hero_count):
            hero_id = bit_reader.read_uint32()
            legends.append(hero_id)
            bit_reader.bit_pos+=96

        output["entities"][entity_id]["legends"] = legends

        bit_reader.bit_pos+=1
        #handycaps
        if bit_reader.read_bool():
            bit_reader.bit_pos+=96

    bit_reader.bit_pos+=32
    
    return output

def read_results(bit_reader: BitReader) -> dict:
    output = {}
    bit_reader.bit_pos+=32
    if bit_reader.read_bool():
        while bit_reader.read_bool():
            entity_id = bit_reader.read_bits(5)
            result = bit_reader.read_bits(16)
            output[entity_id] = result
    bit_reader.bit_pos+=32

    return output



def read_inputs(bit_reader: BitReader):
    data = bit_reader.data
    pos = bit_reader.bit_pos
    while (data[pos >> 3] >> (7 - (pos & 7))) & 1:
        pos+=6
        bit_reader.bit_pos=pos
        input_count = bit_reader.read_uint32()
        pos+=32

        for _ in range(input_count):
            pos+=32
            if (data[pos >> 3] >> (7 - (pos & 7))) & 1:
                pos+=14
            pos+=1
    bit_reader.bit_pos=pos+1

def read_faces(bit_reader: BitReader, is_KO) -> dict:
    output = {}
    while bit_reader.read_bool():
        entity_id = bit_reader.read_bits(5)
        bit_reader.bit_pos+=32
        if is_KO:
            if entity_id in output.keys():
                output[entity_id] += 1
            else:
                output[entity_id] = 1

    return output



# tennine_path = "C:/Users/finnl/BrawlhallaReplays/[10.09] Apocalypse.replay"
# tenten_path = "C:/Users/finnl/BrawlhallaReplays/[10.10] World'sEnd.replay"
# ninezero_path = "C:/Users/finnl/BrawlhallaReplays/[9.01] Apocalypse (10).replay"

#replay_folder_path = "C:/Users/finnl/BrawlhallaReplays"
#replay_folder = Path(replay_folder_path)

#files = [file for file in replay_folder.iterdir() if file.is_file()]
#files.sort(key = lambda file: file.stat().st_mtime)


#print(read_replay_file(files[-120].read_bytes()))
#print(read_replay_file(files[4140]))

#print(read_replay_file(files[-1].read_bytes()))

# def run_batch():
#     for i in range(12000): read_replay_file(files[i].read_bytes())
# run_batch()
# cProfile.run('run_batch()', sort='cumulative')

