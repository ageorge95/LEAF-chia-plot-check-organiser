from logging import getLogger
from json import load,\
    dump
from os import path
from tabulate import tabulate
from subprocess import run,\
    PIPE

class LEAF_back_end():

    _log: getLogger

    def __init__(self,
                 wd_root='',
                 wf_name='catalog.json'):

        super(LEAF_back_end, self).__init__()

        self.wd_root = wd_root
        self.wf_name = wf_name

        if path.isfile('config.json'):
            with open('config.json', 'r') as json_in_handle:
                self.config = load(json_in_handle)
        else:
            self.config = {'check_command_template': {}}
            with open('config.json', 'w') as json_out_handle:
                dump(self.config, json_out_handle)
        if len(self.config['check_command_template']) == 0:
            self._log.error('There are no entries in config ! Please add new entries and restart the tool !')

        if path.isfile(path.join(self.wd_root, self.wf_name)):
            with open(path.join(self.wd_root, self.wf_name), 'r') as json_in_handle:
                self.catalog = load(json_in_handle)
        else:
            self.catalog = {}

    def return_configured_coins(self):
        return list(self.config['check_command_template'].keys())

    def print_raw_output(self,
                         coin,
                         filter_by_input,
                         list_of_filenames
                         ):
        if coin in self.catalog.keys():
            for filename, content in self.catalog[coin].items():
                if (filter_by_input and (filename in list_of_filenames)) or not filter_by_input:
                    self._log.info('Displaying raw output for {}.'.format(filename))
                    self._log.info('\n' + content['output_data'])
        else:
            self._log.warning('{} has no registered plot checks !'.format(coin))

    def print_stored_results(self,
                             coin,
                             filter_by_input,
                             list_of_filenames
                             ):
        if coin in self.catalog.keys():
            # sort the results
            sorted_catalog = dict(sorted(self.catalog[coin].items(), key=lambda x: x[1]['proofs']))

            # reporting phase
            headers = ['Plot filepath', 'Proofs Ratio', 'Valid_Test']
            table_rows = []

            for result in sorted_catalog.items():
                if (filter_by_input and path.basename(result[1]['path']) in list_of_filenames) or not filter_by_input:
                    row = [result[1]['path'], result[1]['proofs'], result[1]['validity']]

                    table_rows.append(row)

            self._log.info('\n' + tabulate(table_rows, headers=headers, tablefmt="grid"))
        else:
            self._log.warning('{} has no registered plot checks !'.format(coin))

    def check_plots(self,
                    list_of_plots_fiepaths: list,
                    coin: str):

        for entry in list_of_plots_fiepaths:
            if not path.isfile(entry):
                self._log.warning('{} is not a valid path. It will be skipped.'.format(entry))
            else:
                if coin != 'SELECT A COIN':
                    plot_name = path.basename(entry)
                    self._log.info('Please wait, now checking plot {}'.format(plot_name))

                    if coin not in self.catalog.keys():
                        self.catalog[coin] = {}

                    if plot_name not in self.catalog[coin].keys():

                        self.catalog[coin][plot_name] = {'path': entry}
                        full_command = self.config['check_command_template'][coin].format(plot_filename=plot_name)
                        output = run(full_command, stderr=PIPE).stderr.decode('utf-8')
                        self.catalog[coin][plot_name]['output_data'] = output
                        self.catalog[coin][plot_name]['proofs'] = float(output.split('Proofs ')[-1].split(', ')[1].split('\u001b[0m')[0])
                        if '1 invalid' in output:
                            self.catalog[coin][plot_name]['validity'] = 'invalid'
                        else:
                            self.catalog[coin][plot_name]['validity'] = 'valid'

                        with open(path.join(self.wd_root, self.wf_name), 'w') as json_out_handle:
                            dump(self.catalog, json_out_handle, indent=2)

                        self._log.info('Check done and result saved for {}: \n{}'.format(plot_name,
                                                                                         self.catalog[coin][plot_name]['output_data']))

                    else:
                        self._log.info('{} already in the stored results. Skipping ...'.format(plot_name))
                else:
                    self._log.warning('Please select a valid coin')
