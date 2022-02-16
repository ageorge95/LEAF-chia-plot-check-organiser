from sys import path
from os import path as os_path, listdir
path.append(os_path.join('chia_blockchain'))
path.append(os_path.join('chives_blockchain'))
from pathlib import Path
from logging import getLogger, StreamHandler, Formatter
from json import load,\
    dump
from tabulate import tabulate
from traceback import format_exc
import chiapos
from blspy import G1Element, PrivateKey, AugSchemeMPL
import blspy

configuration = {'chia__XCH': {'port': 8444,
                               'root': Path(os_path.join(os_path.expanduser("~"),'.chia\mainnet'))},
                 'chives__XCC': {'port': 9699,
                                 'root': Path(os_path.join(os_path.expanduser("~"),'.chives\mainnet'))}}

def parse_plot_info(memo: bytes):
    # Parses the plot info bytes into keys
    if len(memo) == (48 + 48 + 32):
        # This is a public key memo
        return (
            G1Element.from_bytes(memo[:48]),
            G1Element.from_bytes(memo[48:96]),
            PrivateKey.from_bytes(memo[96:]),
        )
    elif len(memo) == (32 + 48 + 32):
        # This is a pool_contract_puzzle_hash memo
        return (
            bytes(memo[:32]),
            G1Element.from_bytes(memo[32:80]),
            PrivateKey.from_bytes(memo[80:]),
        )
    else:
        raise ValueError(f"Invalid number of bytes {len(memo)}")

def _derive_path(sk: PrivateKey, path) -> PrivateKey:
    for index in path:
        sk = AugSchemeMPL.derive_child_sk(sk, index)
    return sk

def master_sk_to_local_sk(master: PrivateKey,
                          port: int) -> PrivateKey:
    return _derive_path(master, [12381, port, 3, 0])

def std_hash(b) -> bytes:
    """
    The standard hash used in many places.
    """
    return bytes(blspy.Util.hash256(bytes(b)))

def generate_taproot_sk(local_pk: G1Element, farmer_pk: G1Element) -> PrivateKey:
        taproot_message: bytes = bytes(local_pk + farmer_pk) + bytes(local_pk) + bytes(farmer_pk)
        taproot_hash: bytes = std_hash(taproot_message)
        return AugSchemeMPL.key_gen(taproot_hash)

def generate_plot_public_key(local_pk: G1Element, farmer_pk: G1Element, include_taproot: bool = False) -> G1Element:
    if include_taproot:
        taproot_sk: PrivateKey = generate_taproot_sk(local_pk, farmer_pk)
        return local_pk + farmer_pk + taproot_sk.get_g1()
    else:
        return local_pk + farmer_pk

class LEAF_back_end():

    _log: getLogger

    def __init__(self,
                 wd_root='',
                 wf_name='LEAF_catalog.json'):

        super(LEAF_back_end, self).__init__()

        self.wd_root = wd_root
        self.wf_name = wf_name
        self.reload_catalog()

    def reload_catalog(self):
        try:
            if os_path.isfile(os_path.join(self.wd_root, self.wf_name)):
                with open(os_path.join(self.wd_root, self.wf_name), 'r') as json_in_handle:
                    self.catalog = load(json_in_handle)
            else:
                self.catalog = {}
        except:
            self._log.error('Oh snap ! An error has occurred while reloading the catalog:\n{}'.format(format_exc(chain=False)))


    def parse_input_and_get_paths(self,
                                  input_data: list):
        self._log.info('Looking for plots in the input data ...')
        self.all_plots_paths = []
        for entry in input_data:
            if os_path.isfile(entry):
                self.all_plots_paths.append(entry)
            elif os_path.isdir(entry):
                self.all_plots_paths += list(filter(lambda x:x.endswith('.plot'), [os_path.join(entry, filename) for filename in listdir(entry)]))
            else:
                self._log.warning(f"{ entry } is neither a valid file nor a valid path !")
        self._log.info(f'Discovered { len(self.all_plots_paths) } plots in the provided filepaths & folder paths.')

        if self._precheck_duplicates():
            raise Exception('Duplicate plots found. Please check the logs and rerun the tool.')
        else:
            self._log.info('The list plots to be checked has been built.')


    def _precheck_duplicates(self):

        precheck_duplicates_helper = [os_path.basename(entry) for entry in self.all_plots_paths]
        duplicates_found = False
        for index, entry in enumerate(precheck_duplicates_helper):
            if precheck_duplicates_helper.count(entry) > 1:
                self._log.warning(f'Found duplicate plot: { self.all_plots_paths[index] }')
                duplicates_found = True

        return duplicates_found

    def print_stored_results(self,
                             plot_type):
        try:
            self.reload_catalog()
            if plot_type in self.catalog.keys():
                # sort the results
                sorted_catalog = dict(sorted(self.catalog[plot_type].items(), key=lambda x: (x[1][-1]['proofs_found'] / x[1][-1]['challenges_tried'])))

                # reporting phase
                headers = ['Plot filepath', 'Challenges', 'Proofs Ratio', 'Valid_Test']
                table_rows = []

                for result in sorted_catalog.items():
                    if os_path.basename(result[1][-1]['path']) in [os_path.basename(entry) for entry in self.all_plots_paths]:
                        ratio = result[1][-1]['proofs_found'] / result[1][-1]['challenges_tried']
                        row = [result[1][-1]['path'],
                               result[1][-1]['challenges_tried'],
                               ratio,
                               'GOOD' if ratio != 0 else 'BAD']

                        table_rows.append(row)

                self._log.info('Found {} plots out of which {} plots were checked in the past by this tool'.format(len(self.all_plots_paths),
                                                                                                                   len(table_rows)))
                self._log.info('\n' + tabulate(table_rows, headers=headers, tablefmt="grid"))
            else:
                self._log.warning('{} has no registered plot checks !'.format(plot_type))
        except:
            self._log.error('Oh snap ! An error has occurred while printing the stored results:\n{}'.format(format_exc(chain=False)))

    def check_plots(self,
                    plot_type: str,
                    nr_challenges: int,
                    progress_callback):
        try:
            self.reload_catalog()

            for plot_index, entry in enumerate(self.all_plots_paths, 1):
                if not os_path.isfile(entry):
                    self._log.warning('{} is not a valid path. It will be skipped.'.format(entry))
                else:
                    plot_name = os_path.basename(entry)
                    self._log.info(f'Please wait, now checking plot {plot_index}/{len(self.all_plots_paths)}: {plot_name}')

                    if plot_type not in self.catalog.keys():
                        self.catalog[plot_type] = {}

                    if plot_name not in self.catalog[plot_type].keys():
                        self.catalog[plot_type][plot_name] = []

                    if (len(self.catalog[plot_type][plot_name]) > 0 and self.catalog[plot_type][plot_name][-1]['challenges_tried'] != nr_challenges)\
                            or len(self.catalog[plot_type][plot_name]) == 0:

                        self.catalog[plot_type][plot_name].append({'path': entry})

                        try:
                            prover = chiapos.DiskProver(entry)
                            verifier = chiapos.Verifier()

                            size = prover.get_size()
                            self._log.info(f'This plot has a size of {size}')
                            assert size == int(entry.split('k')[1].split('-')[0])

                            id = prover.get_id()
                            self._log.info(f'Plot ID: { id.hex() }')

                            (pool_public_key_or_puzzle_hash,
                             farmer_public_key,
                             local_master_sk) = parse_plot_info(prover.get_memo())
                            self._log.info(f'Pool public key/ Puzzle Hash: { pool_public_key_or_puzzle_hash }')
                            self._log.info(f'Farmer public key: { farmer_public_key }')
                            self._log.info(f'Local master sk: { local_master_sk }')

                            pool_public_key: G1Element = None
                            pool_contract_puzzle_hash: bytes = None
                            if isinstance(pool_public_key_or_puzzle_hash, G1Element):
                                pool_public_key = pool_public_key_or_puzzle_hash
                            else:
                                assert isinstance(pool_public_key_or_puzzle_hash, bytes)
                                pool_contract_puzzle_hash = pool_public_key_or_puzzle_hash

                            if pool_public_key:
                                self._log.info(f'OG plot detected with pool public key: { pool_public_key }')
                            if pool_contract_puzzle_hash:
                                self._log.info(f'NFT plot detected with pool contract ph: { pool_contract_puzzle_hash.hex() }')

                            local_sk = master_sk_to_local_sk(master=local_master_sk,
                                                             port=configuration[plot_type]['port'])
                            self._log.info(f'Local sk: { local_sk }')

                            plot_public_key: G1Element = generate_plot_public_key(
                                                    local_sk.get_g1(), farmer_public_key, pool_contract_puzzle_hash is not None
                                                )
                            self._log.info(f'Plot public key: { plot_public_key }\n\n')

                            total_proofs = 0

                            for challenge_index in range(0, nr_challenges):
                                challenge = std_hash(challenge_index.to_bytes(32, "big"))
                                self._log.info(f'Prepared challenge {challenge_index + 1}/{nr_challenges}: { challenge.hex() }')

                                qualities_for_challenge = prover.get_qualities_for_challenge(challenge)

                                self._log.info(f'Found {len( qualities_for_challenge) } proofs for the current challenge.')

                                for quality_index, quality_str in enumerate(prover.get_qualities_for_challenge(challenge)):

                                    proof = prover.get_full_proof(challenge, quality_index)
                                    total_proofs += 1
                                    ver_quality_str = verifier.validate_proof(id, size, challenge, proof)
                                    assert quality_str == ver_quality_str

                                progress_callback(subprogress={'maximum': nr_challenges,
                                                               'value': challenge_index+1}
                                                  )

                            self._log.info(f'DONE. Found { total_proofs } proofs/ { nr_challenges } checks, with a ratio of { total_proofs/nr_challenges }.')
                            self.catalog[plot_type][plot_name][-1].update({'proofs_found': total_proofs,
                                                                           'challenges_tried': nr_challenges})

                        except:
                            self._log.error(f'Found an error while checking {entry} \n{format_exc(chain=False)}')
                            self.catalog[plot_type][plot_name][-1].update({'proofs_found': 0,
                                                                           'challenges_tried': nr_challenges})

                        out_path = os_path.join(self.wd_root, self.wf_name)
                        with open(out_path, 'w') as json_out_handle:
                            dump(self.catalog, json_out_handle, indent=2)
                        self._log.info(f'Data saved in { out_path }')
                    else:
                        self._log.warning(f'Plot already checked in the past, with { nr_challenges } challenges. Skipping ...')

                progress_callback(progress={'maximum': len(self.all_plots_paths),
                                            'value': plot_index}
                                                  )
        except:
            self._log.error('Oh snap ! An error has occurred while checking the plots:\n{}'.format(format_exc(chain=False)))