from logging import getLogger
from json import load
from os import path
from tabulate import tabulate

class LEAF_back_end():

    _log: getLogger

    def __init__(self,
                 wd_root='',
                 wf_name='catalog.json'):

        super(LEAF_back_end, self).__init__()

        self.wd_root = wd_root
        self.wf_name = wf_name

        with open('config.json', 'r') as json_in_handle:
            self.config = load(json_in_handle)

        if path.isfile(path.join(self.wd_root, self.wf_name)):
            with open(path.join(self.wd_root, self.wf_name), 'r') as json_in_handle:
                self.catalog = load(json_in_handle)
        else:
            self.catalog = {}

    def return_configured_coins(self):
        return list(self.config['check_command_template'].keys())

    def print_stored_results(self,
                             coin):
        if coin in self.catalog.keys():
            # sort the results
            sorted_catalog = dict(sorted(self.catalog[coin].items(), key=lambda x: x[1]['proofs']))

            # reporting phase
            headers = ['Plot filepath', 'Valid_Test', 'Proofs']
            table_rows = []

            for result in sorted_catalog.items():
                row = [result[1]['path'], result[1]['proofs'], result[1]['validity']]

                table_rows.append(row)

            self._log.info('\n' + tabulate(table_rows, headers=headers, tablefmt="grid"))
        else:
            self._log.warning('{} has no registered plot checks !'.format(coin))

    def check_plots(self,
                    list_of_plots_fiepaths: list):
        pass
