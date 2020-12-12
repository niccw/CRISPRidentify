from os.path import basename
from components_evaluated_arrays_enhancement import IterativeDegeneratedSearch
from components_evaluated_arrays_enhancement import create_boundaries_for_intervals
from components_evaluated_arrays_enhancement import ArrayRefinerInsertionsDeletions
from components_detection_refinement import AdvancedFuzzySearchFilter


class EvaluatedArraysEnhancement:
    def __init__(self, file_path, categories, parameters, flag_dev_mode):
        self.file_path = file_path
        self.categories = categories
        self.parameters = parameters
        self.flag_dev_mode = flag_dev_mode

        self.bona_fide_arrays = categories[0]
        self.possible_arrays = categories[2]

        self.dict_arrays_into_categories_enhanced = {}

        self._get_complete_dna()
        self._search_missed_or_degenerated_repeats()
        self._refine_nucleotides_repeat_spacer()
        self._filter_enhanced()

    def _get_complete_dna(self):
        with open(self.file_path, 'r') as f:
            lines = f.readlines()

        self.input_header = lines[0]
        self.dna = ''.join([line.strip() for line in lines[1:]])
        self.dna_length = len(self.dna)
        self.dna = self.dna.upper()

    def _search_missed_or_degenerated_repeats(self):
        intervals = []
        arrays = []
        for interval, list_data in self.bona_fide_arrays.items():
            intervals.append(interval)
            arrays.append(list_data[0][1])

        boundaries = create_boundaries_for_intervals(intervals, 500)

        for interval, array, boundary in zip(intervals, arrays, boundaries):

            consensus = array.consensus
            list_repeats = array.list_repeats
            list_repeats_starts = array.list_repeat_starts
            list_spacers = array.list_spacers

            try:
                ids = IterativeDegeneratedSearch(full_dna=self.dna,
                                                 repeat_seq_candidate=consensus,
                                                 spacer_margin=self.parameters["param_spacer_margin_degenerated_search"],
                                                 repeat_seq_candidate_gaped=None,
                                                 list_repeats_starts=list_repeats_starts,
                                                 list_repeats=list_repeats,
                                                 list_spacers=list_spacers,
                                                 start_flanking_region_left=boundary[0],
                                                 end_flanking_region_right=boundary[1],
                                                 allowed_max_editing_distance=self.parameters["param_max_edit_distance"],
                                                 iterative_size_flanking_region=150,
                                                 prevent_long_spacers=True,
                                                 attempt_to_improve_initial_array=True)

                new_crispr_candidate = ids.output()

                if self.flag_dev_mode:
                    if array != new_crispr_candidate:
                        with open("log.txt", "a") as f:
                            acc_num = basename(self.file_path).split(".")[0]
                            f.write(f"Iteractive degenerated search {acc_num}\n")
                            f.write(array.dot_repr())
                            f.write("\n\n")
                            f.write(new_crispr_candidate.dot_repr())
                            f.write("\n\n")

            except Exception:
                new_crispr_candidate = array

                if self.flag_dev_mode:
                    with open("log_error.txt", "a") as f:
                        acc_num = basename(self.file_path).split(".")[0]
                        f.write(f"Iteractive degenerated search error {acc_num}\n")
                        f.write(array.dot_repr())
                        f.write("\n\n")

            self.bona_fide_arrays[interval][0][1] = new_crispr_candidate

    def _refine_nucleotides_repeat_spacer(self):
        intervals = []
        arrays = []
        for interval, list_data in self.bona_fide_arrays.items():
            intervals.append(interval)
            arrays.append(list_data[0][1])

        for interval, array in zip(intervals, arrays):
            try:
                arid = ArrayRefinerInsertionsDeletions(array)
                new_crispr_candidate = arid.output()

                if self.flag_dev_mode:
                    if array != new_crispr_candidate:
                        with open("log.txt", "a") as f:
                            acc_num = basename(self.file_path).split(".")[0]
                            f.write(f"Array refinement {acc_num}\n")
                            f.write(array.dot_repr())
                            f.write("\n\n")
                            f.write(new_crispr_candidate.dot_repr())
                            f.write("\n\n")

            except Exception:
                new_crispr_candidate = array

                if self.flag_dev_mode:
                    with open("log_error.txt", "a") as f:
                        acc_num = basename(self.file_path).split(".")[0]
                        f.write(f"Array refinement error {acc_num}\n")
                        f.write(array.dot_repr())
                        f.write("\n\n")

            self.bona_fide_arrays[interval][0][1] = new_crispr_candidate

        self.categories[0] = self.bona_fide_arrays

    def _filter_enhanced(self):
        self.param_min_avg_repeat_length = self.parameters["param_min_avg_repeat_length"]
        self.param_max_avg_repeat_length = self.parameters["param_max_avg_repeat_length"]
        self.param_min_avg_spacer_length = self.parameters["param_min_avg_spacer_length"]
        self.param_max_avg_spacer_length = self.parameters["param_max_avg_spacer_length"]
        self.param_min_repeats = self.parameters["param_min_repeats"]
        self.param_max_identical_spacers = self.parameters["param_max_identical_spacers"]
        self.param_max_identical_cluster_spacers = self.parameters["param_max_identical_cluster_spacers"]

        afsf = AdvancedFuzzySearchFilter(min_column_dominance_repeat=0.6,
                                         max_spacer_length=140, max_column_dominance_spacer=0.8,
                                         max_allowed_consecutive_spacers=self.param_max_identical_cluster_spacers,
                                         max_allowed_same_spacers=self.param_max_identical_spacers,
                                         max_inconsistent_columns=5,
                                         min_avg_repeat_length=self.param_min_avg_repeat_length,
                                         max_avg_repeat_length=self.param_max_avg_repeat_length,
                                         min_avg_spacer_length=self.param_min_avg_spacer_length,
                                         max_avg_spacer_length=self.param_max_avg_spacer_length,
                                         min_repeats=self.param_min_repeats)

        bona_fide_not_filtered = self.categories[0]
        low_score = self.categories[4]
        bona_fide_filtered = {}

        for key, value in bona_fide_not_filtered.items():
            crispr = value[0][1]
            if not afsf(crispr):
                if key in low_score:
                    low_score[key].append(value[0])
                else:
                    low_score[key] = value
            else:
                bona_fide_filtered[key] = value

        self.categories[0] = bona_fide_filtered
        self.categories[4] = low_score

    def output(self):
        return self.categories