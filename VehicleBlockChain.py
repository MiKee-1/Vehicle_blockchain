import hashlib
import json
import datetime
import os
import logging
from typing import List, Dict, Any, Optional

# logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vehicle_blockchain.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("VehicleBlockchain")

class Block:
    """
    A block in the blockchain
    
    Attributes:
        index (int): position of the block in the.
        timestamp (str): time of block creation in ISO format.
        data (dict): Data in the block.
        previous_hash (str): Hash of previous block.
        hash (str): Hash of this block.
        nonce (int): proof of work.
    """
    
    def __init__(self, index: int, timestamp: str, data: dict, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.hash_block()
    
    def hash_block(self) -> str:
        # claculating hash sha256
        try:
            block_string = f"{self.index}{self.timestamp}{json.dumps(self.data, sort_keys=True)}{self.previous_hash}{self.nonce}"
            return hashlib.sha256(block_string.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Errore durante il calcolo dell'hash: {e}")
            raise
    
    def mine_block(self, difficulty: int) -> None:
        """
        proof of work
        
        Args:
            difficulty (int): Number of 0 at the beginning of hash
        """
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.hash_block()
        logger.info(f"Blocco minato: {self.hash}")

class VehicleBlockchain:
    """
    this manage the blockchain for tracking vehicles
    
    Attributes:
        chain (List[Block): chain
        difficulty (int): Difficulty of proof of work
        data_file (str): file path
    """
    
    def __init__(self, difficulty: int = 2, data_file: str = "blockchain_data.json"):
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.data_file = data_file
        
        # create the chain o add the block
        if os.path.exists(data_file):
            self.load_chain()
        else:
            self.create_genesis_block()
    
    def create_genesis_block(self) -> None:
        #creating genesis block
        genesis_block = Block(
            index=0,
            timestamp=datetime.datetime.now().isoformat(),
            data={"message": "Blocco Genesi"},
            previous_hash="0"
        )
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        logger.info("Blocco genesi creato")
        self.save_chain()
    
    def add_data(self, vehicle_id: str, sensor_data: dict) -> bool:
        """
        adding data to blockchain
        
        Args:
            vehicle_id (str): vehicle ID
            sensor_data (dict): sensor data
            
        Returns:
            bool: True if the block is added with no errors
        """
        try:
            self._validate_data(vehicle_id, sensor_data)
            
            previous_block = self.chain[-1]
            new_block = Block(
                index=len(self.chain),
                timestamp=datetime.datetime.now().isoformat(),
                data={
                    "vehicle_id": vehicle_id,
                    "sensor_data": sensor_data,
                    "signature": self._generate_signature(vehicle_id, sensor_data)
                },
                previous_hash=previous_block.hash
            )
            
            new_block.mine_block(self.difficulty)
            self.chain.append(new_block)
            logger.info(f"New Block Added {vehicle_id}")
            
            self.save_chain()
            return True
        except Exception as e:
            logger.error(f"Loading Error: {e}")
            return False
    
    def _validate_data(self, vehicle_id: str, sensor_data: dict) -> None:
        """
        #verify the correct format of the data
        
        Args:
            vehicle_id (str): Vehicle ID.
            sensor_data (dict): sensor data.
            
        Raises:
            ValueError: if data are not in a valid format.
        """
        if not vehicle_id or not isinstance(vehicle_id, str):
            raise ValueError("Vehicle ID must be a not-empty string")
        
        if not isinstance(sensor_data, dict):
            raise ValueError("sensor data must be a dictionary")
    
    def _generate_signature(self, vehicle_id: str, sensor_data: dict) -> str:
        """
        digital signature
        
        Args:
            vehicle_id (str): Vehicle ID.
            sensor_data (dict): sensor data
            
        Returns:
            str: digital signature.
        """
        # Here you can use a library for cryptography

        data_string = f"{vehicle_id}{json.dumps(sensor_data, sort_keys=True)}"
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def is_chain_valid(self) -> bool:
        """
        verify blockchain
        
        Returns:
            bool: True if blockchain is valid
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            
            # verify current hash
            if current.hash != current.hash_block():
                logger.warning(f"Hash invalido nel blocco {i}")
                return False
            
            # Verify previous hash
            if current.previous_hash != previous.hash:
                logger.warning(f"Collegamento rotto tra blocchi {i-1} e {i}")
                return False
        
        logger.info("Blockchain verified: Valid")
        return True
    
    def save_chain(self) -> None:
        """save the blockchain in a file."""
        try:
            data = []
            for block in self.chain:
                block_data = {
                    "index": block.index,
                    "timestamp": block.timestamp,
                    "data": block.data,
                    "previous_hash": block.previous_hash,
                    "nonce": block.nonce,
                    "hash": block.hash
                }
                data.append(block_data)
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=4)
            
            logger.info(f"Blockchain saved in {self.data_file}")
        except Exception as e:
            logger.error(f"Saving error: {e}")
    
    def load_chain(self) -> None:
        """load blockchain from file."""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            self.chain = []
            for block_data in data:
                block = Block(
                    index=block_data["index"],
                    timestamp=block_data["timestamp"],
                    data=block_data["data"],
                    previous_hash=block_data["previous_hash"]
                )
                block.nonce = block_data["nonce"]
                block.hash = block_data["hash"]
                self.chain.append(block)
            
            logger.info(f"Blockchain loaded from {self.data_file}")
        except Exception as e:
            logger.error(f"Loading error: {e}")
            self.create_genesis_block()
    
    def get_block_by_vehicle_id(self, vehicle_id: str) -> List[Block]:
        """
        finds all the blocks of a vehicle
        
        Args:
            vehicle_id (str): vehicle id you want to find
            
        Returns:
            List[Block]: blocklist of the vehicle
        """
        return [block for block in self.chain 
                if block.index > 0 and block.data.get("vehicle_id") == vehicle_id]


if __name__ == "__main__":
    # Creare una blockchain con difficoltà 2
    bc = VehicleBlockchain(difficulty=2)
    
    # adding example data
    bc.add_data("LAMB-001", {
        "oil_level": "low",
        "brake_wear": "75%",
        "engine_temp": "normal",
        "error_code": None,
        "km_totali": 15000,
        "last_maintainance": "2025-04-15"
    })
    
    bc.add_data("FERR-002", {
        "oil_level": "normal",
        "brake_wear": "25%",
        "engine_temp": "high",
        "error_code": "P0301",
        "km_totali": 8500,
        "last_maintainance": "2025-01-20"
    })
    
    
    print("Blockchain valida:", bc.is_chain_valid())
    
    # searching blocks for a specific vehicle
    lamb_blocks = bc.get_block_by_vehicle_id("LAMB-001")
    print(f"\nBlocchi per LAMB-001: {len(lamb_blocks)}")
    for block in lamb_blocks:
        print(json.dumps(block.data, indent=2))
    
    # printing blockchain
    print("\n BLOCKCHAIN COMPLETED:")
    for block in bc.chain:
        print(f"Blocco #{block.index} | Hash: {block.hash[:10]}... | Timestamp: {block.timestamp}")
