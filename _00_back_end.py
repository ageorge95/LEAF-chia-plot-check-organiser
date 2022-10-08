from os import path,\
    listdir,\
    mkdir
from logging import getLogger
from json import load,\
    dump
from tabulate import tabulate
from traceback import format_exc
import chiapos
from blspy import G1Element, PrivateKey, AugSchemeMPL
import blspy
from time import sleep
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from typing import List

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
    
class output_manager():
    def __init__(self):
        self._log = getLogger()

        if not path.isdir('output'):
            mkdir('output')

    def load_data(self,
                  plot_name):
        if not path.isfile(path.join('output', plot_name+'.json')):
            return None
        else:
            try:
                with open(path.join('output', plot_name+'.json'), 'r') as input_handle:
                    return load(input_handle)
            except:
                return None

    def save_data(self,
                  plot_name,
                  content):
        max_retry = 5
        current_try = -1
        while True:
            current_try += 1
            if current_try == max_retry:
                self._log.error(f"Max retries reached while trying to load the json for { plot_name }.")
                raise Exception
            try:
                with open(path.join('output', plot_name+'.json'), 'w') as output_handle:
                    dump(content, output_handle, indent=2)
                break
            except:
                current_try += 1
                self._log.warning(f"Error found while trying to load the json for { plot_name }."
                                  f" Will retry in 5 sec. Retry { current_try } / { max_retry }\n{format_exc(chain=False)}")
                sleep(5)

    def get_entries(self):
        return listdir('output')

    def parse_and_return_relevant_data(self,
                                       list_of_plots):
        to_return = []
        for plot_name in list_of_plots:
            stored_data = self.load_data(plot_name)
            if stored_data:
                to_return.append({'name': plot_name,
                                  'challenges_tried': max(int(_) for _ in stored_data['challenges'].keys())+1,
                                  'proofs_found': sum([_['proofs'] for _ in stored_data['challenges'].values()])})
            else:
                to_return.append({'name': plot_name,
                                  'challenges_tried': None,
                                  'proofs_found': None})
        return to_return

class LEAF_back_end(output_manager):

    _log: getLogger

    def __init__(self,
                 wd_root='',
                 wf_name='LEAF_catalog.json'):

        super(LEAF_back_end, self).__init__()

        self.wd_root = wd_root
        self.wf_name = wf_name

    def build_distribution_graph(self,
                                 proofs_found_list: List,
                                 proofs_checked_list: List):

        fig = make_subplots(rows=2, cols=1)

        # add the proofs_found histogram
        fig.add_trace(go.Histogram(x=proofs_found_list,
                                   name='proofs_found',
                                   marker=dict(color='green')),
                      row=1,col=1)

        # add the proofs_found histogram
        fig.add_trace(go.Histogram(x=proofs_checked_list,
                                   name='proofs_checked',
                                   marker=dict(color='blue')),
                      row=2, col=1)
        fig.show()

    def parse_input_and_get_paths(self,
                                  input_data: list):
        self._log.info('Looking for plots in the input data ...')
        self.all_plots_paths = []
        for entry in input_data:
            if path.isfile(entry):
                self.all_plots_paths.append(entry)
            elif path.isdir(entry):
                self.all_plots_paths += list(filter(lambda x:x.endswith('.plot'), [path.join(entry, filename) for filename in listdir(entry)]))
            else:
                self._log.warning(f"{ entry } is neither a valid file nor a valid path !")
        self._log.info(f'Discovered { len(self.all_plots_paths) } plots in the provided filepaths & folder paths.')

        if self._precheck_duplicates():
            raise Exception('Duplicate plots found. Please check the logs and rerun the tool.')
        else:
            self._log.info('The list plots to be checked has been built.')


    def _precheck_duplicates(self):

        precheck_duplicates_helper = [path.basename(entry) for entry in self.all_plots_paths]
        duplicates_found = False
        for index, entry in enumerate(precheck_duplicates_helper):
            if precheck_duplicates_helper.count(entry) > 1:
                self._log.warning(f'Found duplicate plot: { self.all_plots_paths[index] }')
                duplicates_found = True

        return duplicates_found

    def trigger_histogram_build(self) -> None:
        try:

            list_with_all_plots = self.parse_and_return_relevant_data([path.basename(_) for _ in self.all_plots_paths])

            # filter plots with no past checks
            checked_plots = list(filter(lambda x:x['challenges_tried'], list_with_all_plots))

            if len(checked_plots)>0:
                self.build_distribution_graph(proofs_found_list=[x['proofs_found'] / x['challenges_tried'] for x in checked_plots],
                                              proofs_checked_list=[x['challenges_tried'] for x in checked_plots])
        except:
            self._log.error('Oh snap ! An error has occurred while printing the stored results:\n{}'.format(format_exc(chain=False)))

    def print_stored_results(self,
                             filter_by):
        try:

            list_with_all_plots = self.parse_and_return_relevant_data([path.basename(_) for _ in self.all_plots_paths])

            # filter plots with no past checks
            not_checked_plots = list(filter(lambda x:not x['challenges_tried'], list_with_all_plots))
            checked_plots = list(filter(lambda x:x['challenges_tried'], list_with_all_plots))

            # sort the results
            sorted_checked_plots = sorted(checked_plots,
                                 key=lambda x: ((x['proofs_found'] / x['challenges_tried']) if filter_by == 'proofs_found'
                                                else x['challenges_tried'] if filter_by == 'challenges_tried'
                                                else x['proofs_found']))

            # reporting phase
            headers = ['Plot name', 'Challenges', 'Proofs Ratio']
            table_rows = []

            for result in sorted_checked_plots+not_checked_plots:
                ratio = (result['proofs_found'] / result['challenges_tried'])\
                    if result['challenges_tried'] else 0
                row = [result['name'],
                       result['challenges_tried'],
                       ratio]

                table_rows.append(row)

            self._log.info('\n' + tabulate(table_rows, headers=headers, tablefmt="grid"))
        except:
            self._log.error('Oh snap ! An error has occurred while printing the stored results:\n{}'.format(format_exc(chain=False)))

    def check_plots(self,
                    nr_challenges: int,
                    delay_between_checks: float,
                    progress_callback,
                    stop_flag_check):
        try:

            # reset the progress bar
            progress_callback(subprogress={'maximum': 0,
                                           'value': 0,
                                           'text': f'0 / { nr_challenges }'},
                              progress={'maximum': 0,
                                        'value': 0,
                                        'text': f'0 / { len(self.all_plots_paths) }'})

            for plot_index, plot_path in enumerate(self.all_plots_paths, 1):
                if stop_flag_check():
                    self._log.warning('STOP requested by the user. Do not worry,'
                                      ' on the next execution the plot check will resume where it left off.')
                    return

                if not path.isfile(plot_path):
                    self._log.warning('{} is not a valid path. It will be skipped.'.format(plot_path))
                else:
                    plot_name = path.basename(plot_path)
                    self._log.info(f'Please wait, now checking plot {plot_index}/{len(self.all_plots_paths)}: {plot_name}')

                    existing_data_for_plot = self.load_data(plot_name)
                    working_set = existing_data_for_plot if existing_data_for_plot else {'challenges': {},
                                                                                         'path_history': []}

                    working_set['path_history'].append(plot_path)
                    working_set['path_history'] = working_set['path_history'][-5:]

                    try:
                        # only do the checks below if the plots has not been fully checked before
                        # this check saves some I/O requests
                        if nr_challenges > len(working_set['challenges'].keys()):
                            prover = chiapos.DiskProver(plot_path)
                            verifier = chiapos.Verifier()

                            size = prover.get_size()
                            self._log.info(f'This plot has a size of {size}')
                            working_set['plot_size'] = size
                            # sanity check - check if the parsed plot size is the same as in the plot filename
                            assert size == int(plot_path.split('k')[1].split('-')[0])

                            id = prover.get_id()
                            working_set['plot_id'] = id.hex()
                            self._log.info(f'Plot ID: { id.hex() }')

                            (pool_public_key_or_puzzle_hash,
                             farmer_public_key,
                             local_master_sk) = parse_plot_info(prover.get_memo())
                            working_set['farmer_public_key'] = str(farmer_public_key)
                            working_set['local_master_sk'] = str(local_master_sk)
                            working_set['pool_public_key_or_puzzle_hash'] = str(pool_public_key_or_puzzle_hash)

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
                                working_set['plot_type'] = 'OG'
                            if pool_contract_puzzle_hash:
                                self._log.info(f'NFT plot detected with pool contract ph: { pool_contract_puzzle_hash.hex() }')
                                working_set['plot_type'] = 'NFT'

                            for port in [['chia-XCH', 8444],
                                         ['chives-XCC', 9699]]:
                                local_sk = master_sk_to_local_sk(master=local_master_sk,
                                                                 port=port[1])
                                self._log.info(f'Local sk: { local_sk }')

                                plot_public_key: G1Element = generate_plot_public_key(
                                                        local_sk.get_g1(), farmer_public_key, pool_contract_puzzle_hash is not None
                                                    )
                                working_set[f'plot_public_key_{ port[1] }'] = str(plot_public_key)
                                self._log.info(f'Plot public key for port { port[0] } -> { port[1] }: { plot_public_key }\n\n')

                            self.save_data(plot_name,
                                           working_set)
                            total_proofs = 0

                            for challenge_index in range(0, nr_challenges):
                                if stop_flag_check():
                                    self._log.warning('STOP requested by the user. Do not worry,'
                                                      ' on the next execution the plot check will resume where it left off.')
                                    return

                                self._log.info(f'Checking challenge {challenge_index + 1}/{nr_challenges} ...')

                                if str(challenge_index) not in working_set['challenges'].keys():
                                    challenge = std_hash(challenge_index.to_bytes(32, "big"))
                                    working_set['challenges'][challenge_index] = {'challenge': challenge.hex()}
                                    self._log.info(f'Prepared challenge {challenge_index + 1}/{nr_challenges}: { challenge.hex() }')

                                    qualities_for_challenge = prover.get_qualities_for_challenge(challenge)

                                    working_set['challenges'][challenge_index]['proofs'] = len(qualities_for_challenge)
                                    self._log.info(f'Found { len(qualities_for_challenge) } proofs for the current challenge.')

                                    # verify the proof
                                    for quality_index, quality_str in enumerate(qualities_for_challenge):

                                        proof = prover.get_full_proof(challenge, quality_index)
                                        total_proofs += 1
                                        ver_quality_str = verifier.validate_proof(id, size, challenge, proof)
                                        assert quality_str == ver_quality_str

                                    progress_callback(subprogress={'maximum': nr_challenges,
                                                                   'value': challenge_index+1,
                                                                   'text': f"{ challenge_index+1 } / { nr_challenges }"}
                                                      )
                                    self.save_data(plot_name,
                                                   working_set)

                                    if delay_between_checks:
                                        self._log.info(f"Going to sleep for { delay_between_checks } seconds ...")
                                        sleep(delay_between_checks)
                                else:
                                    self._log.info('This challenge was already checked for this plot.')
                                    total_proofs += working_set['challenges'][str(challenge_index)]['proofs']

                            self._log.info(f'DONE. Found { total_proofs } proofs/ { nr_challenges } checks, with a ratio of { total_proofs/nr_challenges }.')

                    except:
                        self._log.error(f'Found an error while checking {plot_path} \n{format_exc(chain=False)}')

                progress_callback(progress={'maximum': len(self.all_plots_paths),
                                            'value': plot_index,
                                            'text': f"{ plot_index } / { len(self.all_plots_paths) }"})

        except:
            self._log.error('Oh snap ! An error has occurred while checking the plots:\n{}'.format(format_exc(chain=False)))