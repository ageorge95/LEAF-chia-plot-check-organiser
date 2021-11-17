from sys import path
from os import path as os_path, listdir
path.append(os_path.join('chia_blockchain'))
path.append(os_path.join('chives_blockchain'))

from io import StringIO
from yaml import safe_load
from pathlib import Path
from logging import getLogger, StreamHandler, Formatter
from json import load,\
    dump
from tabulate import tabulate
from traceback import format_exc
from chia_blockchain.chia.plotting.check_plots import check_plots as check_plots_chia
from chives_blockchain.chives.plotting.check_plots import check_plots as check_plots_chives

configuration = {'chia__XCH': {'logic': check_plots_chia,
                               'root': Path(os_path.join(os_path.expanduser("~"),'.chia\mainnet'))},
                 'chives__XCC': {'logic': check_plots_chives,
                               'root': Path(os_path.join(os_path.expanduser("~"),'.chives\mainnet'))}}

class LEAF_back_end():

    _log: getLogger

    def __init__(self,
                 wd_root='',
                 wf_name='catalog.json'):

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

    def get_filenames_from_yaml(self,
                                coin):
        try:
            with open(os_path.join(configuration[coin]['root'], 'config', 'config.yaml'), 'r') as yaml_in_handle:
                yaml_as_dict = safe_load(yaml_in_handle)
                valid_paths = []
                for current_path in yaml_as_dict['harvester']['plot_directories']:
                    if os_path.isdir(current_path):
                        valid_paths.append(current_path)
                return list(filter(lambda x:x.endswith('.plot'), [os_path.join(entry, plot_filepath) for entry in valid_paths for plot_filepath in listdir(entry)]))
        except:
            self._log.error('Oh snap ! An error has occurred while getting the filenames from the yaml:\n{}'.format(format_exc(chain=False)))

    def precheck_duplicates(self,
                            coin):
        try:
            all_plots_data = [[entry, os_path.basename(entry)] for entry in self.get_filenames_from_yaml(coin=coin)]
            all_plots_filenames = [entry[1] for entry in all_plots_data]

            duplicates = []
            for plot_data in all_plots_data:
                if all_plots_filenames.count(plot_data[1]) > 1:
                    duplicates.append(plot_data[0])
                    if coin in self.catalog.keys():
                        if plot_data[1] in self.catalog[coin].keys():
                            del self.catalog[coin][plot_data[1]]

            if duplicates:
                self._log.warning('Duplicates were found. {} plots were checked. Please resolve the conflicts then restart the tool.'
                                  ' Duplicate plots were automatically removed from the catalog. Conflicts:'.format(len(all_plots_filenames))+ '\n'.join(duplicates))
                return False
            else:
                self._log.info('No duplicates were found. {} plots were checked. Continuing'.format(len(all_plots_filenames)))
                return True
        except:
            self._log.error('Oh snap ! An error has occurred while checking for duplicates:\n{}'.format(format_exc(chain=False)))

    def print_raw_output(self,
                         coin,
                         filter_string):
        try:
            self.reload_catalog()
            if filter_string:
                if coin in self.catalog.keys():
                    for filename, content in self.catalog[coin].items():
                        if filter_string in filename or filename in filter_string:
                            self._log.info('Displaying raw output for {}.'.format(filename))
                            self._log.info('\n' + content['output_data'])
                else:
                    self._log.warning('{} has no registered plot checks !'.format(coin))
        except:
            self._log.error('Oh snap ! An error has occurred while printing the raw data:\n{}'.format(format_exc(chain=False)))

    def print_stored_results(self,
                             coin):
        try:
            self.reload_catalog()
            if coin in self.catalog.keys():
                # sort the results
                sorted_catalog = dict(sorted(self.catalog[coin].items(), key=lambda x: x[1]['proofs']))
                registered_plots = self.get_filenames_from_yaml(coin=coin)

                # reporting phase
                headers = ['Plot filepath', 'Proofs Ratio', 'Valid_Test']
                table_rows = []

                for result in sorted_catalog.items():
                    if os_path.basename(result[1]['path']) in [os_path.basename(entry) for entry in registered_plots]:
                        row = [result[1]['path'], result[1]['proofs'], result[1]['validity']]

                        table_rows.append(row)

                self._log.info('Found {} plots configured in the yaml out of which {} plots were checked in the past by this tool'.format(len(registered_plots),
                                                                                                                                          len(table_rows)))
                self._log.info('\n' + tabulate(table_rows, headers=headers, tablefmt="grid"))
            else:
                self._log.warning('{} has no registered plot checks !'.format(coin))
        except:
            self._log.error('Oh snap ! An error has occurred while printing the stored results:\n{}'.format(format_exc(chain=False)))

    def check_plots(self,
                    coin: str,
                    list_of_plots_filepaths: list = None,
                    ):
        try:
            self.reload_catalog()
            if not list_of_plots_filepaths:
                list_of_plots_filepaths = self.get_filenames_from_yaml(coin=coin)

            for index, entry in enumerate(list_of_plots_filepaths, 1):
                if not os_path.isfile(entry):
                    self._log.warning('{} is not a valid path. It will be skipped.'.format(entry))
                else:
                    plot_name = os_path.basename(entry)
                    self._log.info('Please wait, now checking plot {}/{}: {}'.format(index,
                                                                                     len(list_of_plots_filepaths),
                                                                                     plot_name))

                    if coin not in self.catalog.keys():
                        self.catalog[coin] = {}

                    if plot_name not in self.catalog[coin].keys():

                        self.catalog[coin][plot_name] = {'path': entry}

                        buffer = StringIO()
                        self.logHandler = StreamHandler(buffer)
                        formatter = Formatter('%(asctime)s,%(msecs)d %(levelname)-4s [%(filename)s:%(lineno)d -> %(name)s - %(funcName)s] ___ %(message)s')
                        self.logHandler.setFormatter(formatter)
                        self._log.addHandler(self.logHandler)

                        configuration[coin]['logic'](root_path=configuration[coin]['root'],
                                                    num=None,
                                                    challenge_start=None,
                                                    grep_string=plot_name,
                                                    list_duplicates=False,
                                                    debug_show_memo=None)

                        self._log.removeHandler(self.logHandler)
                        output = buffer.getvalue()

                        self.catalog[coin][plot_name]['output_data'] = str(output)
                        try:
                            self.catalog[coin][plot_name]['proofs'] = float(self.catalog[coin][plot_name]['output_data'].split('Proofs ')[-1].split(', ')[1].split('\n')[0])
                        except:
                            try:
                                self.catalog[coin][plot_name]['proofs'] = float(self.catalog[coin][plot_name]['output_data'].split('Proofs ')[-1].split(', ')[1].split('\u001b[0m')[0])
                            except:
                                self.catalog[coin][plot_name]['proofs'] = 0

                        if '1 valid' in self.catalog[coin][plot_name]['output_data']:
                            self.catalog[coin][plot_name]['validity'] = 'valid'
                        else:
                            self.catalog[coin][plot_name]['validity'] = 'invalid'

                        with open(os_path.join(self.wd_root, self.wf_name), 'w') as json_out_handle:
                            dump(self.catalog, json_out_handle, indent=2)

                        self._log.info('Check done and result saved for {}'.format(plot_name))

                    else:
                        self._log.info('{} already in the stored results. Skipping ...'.format(plot_name))
        except:
            self._log.error('Oh snap ! An error has occurred while checking the plots:\n{}'.format(format_exc(chain=False)))
