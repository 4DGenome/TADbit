"""
28 Jan 2013

Sample script in order to analyze and compare the topology of TADs.

"""

from pytadbit import Chromosome
from pytadbit.tad_clustering.tad_cmo import optimal_cmo
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import dendrogram
from scipy.cluster.hierarchy import linkage
import multiprocessing as mu

PATH =  'sample_data/'
# rewrite get_distance looking at ledily compare_tads

def main():
    test_chr = Chromosome(name='Test Chromosome')
    test_chr.add_experiment('exp1', 100000, xp_handler=PATH +
                            'HIC_k562_chr19_chr19_100000_obs.txt')
    test_chr.find_tad(['exp1'])
    tad_names = []
    tad_matrices = []
    for name, matrix in test_chr.iter_tads('exp1'):
        if test_chr.experiments['exp1'].tads[name]['score'] < 0:
            continue
        if (test_chr.experiments['exp1'].tads[name]['end'] -
            test_chr.experiments['exp1'].tads[name]['start']) < 10:
            continue
        tad_names.append(name)
        tad_matrices.append(matrix)
    num = len(tad_names)
    distances, cci = get_distances(tad_matrices, max_num_v=mu.cpu_count())
    results, clusters = pre_cluster(distances, cci, num)
    paint_clustering(results, clusters, num, test_chr, tad_names)


def get_distances(tad_matrices, max_num_v=8, n_cpus=8):
    """
    Calculates distances between all pair of tads in the chromosome.
    several CPUs can be used.
    :param tad_matrices: all tads in form {1:[hi-c_list], 2:[hi-c_list]...}
    :param 6 num_v: maximum number of eigenvector to use in the alignment (the
       more the slower... but the better the approximation). Number higher than
       15 should not be considered.
    :param 4 n_cpus: number of CPUs to use
    
    :returns: a dict of distances
    """
    num = len(tad_matrices)
    distances = {}
    cci = {}
    jobs = {}
    pool = mu.Pool(n_cpus)
    for i in xrange(num):
        for j in xrange(i+1, num):
            jobs[(i, j)] = pool.apply_async(
                optimal_cmo, args=(tad_matrices[i], tad_matrices[j]),
                kwds={'max_num_v': max_num_v, 'method': 'frobenius'})
    pool.close()
    pool.join()
    for i in xrange(num):
        for j in xrange(i + 1, num):
            _, _, sc = jobs[(i, j)].get()
            # 0.0001 has shown to be a fair cutoff for p-values for square matrix
            # comparison
            if sc['pval'] < 0.0001:
                cci.setdefault(i, []).append(j)
                distances[(i, j)] = sc['dist']
    return distances, cci


def pre_cluster(distances, cci, num):
    """
    """
    clusters = []
    list_nodes = cci.keys()
    while list_nodes:
        node = list_nodes.pop()
        found = False
        for cluster in clusters:
            if node in cluster:
                found = True
                cluster = list(set(cluster+cci.get(node, [])))
        if not found:
            clusters.append(list(set([node] + cci.get(node, []))))
        while True:
            for i, cluster1 in enumerate(clusters):
                for j, cluster2 in enumerate(clusters[i+1:]):
                    if set(cluster1) & set(cluster2):
                        clusters[i] = list(set(cluster1+cluster2))
                        del(clusters[i+j+1])
                        break
                else:
                    continue
                break
            else:
                break
    results = [[[0 for _ in xrange(len(i))] for _ in xrange(len(i))] \
               for i in clusters]
    for k, cluster in enumerate(clusters):
        trans = [i for i in xrange(num) if i in cluster]
        for i in xrange(num):
            for j in xrange(i + 1, num):
                if not (i in cluster and j in cluster):
                    continue
                if not (i, j) in distances:
                    continue
                results[k][trans.index(i)][trans.index(j)] = distances[(i, j)]
                results[k][trans.index(j)][trans.index(i)] = distances[(i, j)]
    return results, clusters


def paint_clustering(results, clusters, num, chrom, tad_names):
    dendros = []
    axes = []
    prev = 0
    xlim = [-100, 100]
    tmp = []
    for i, result in enumerate(results):
        if axes:
            axes[-1].set_xticklabels([], visible=False)
        clust = linkage(result, method='ward')
        tmp = dendrogram(clust, orientation='right', no_plot=True)['leaves']
        dendros += reversed(list([clusters[i][n] for n in tmp]))
        axes.append(plt.subplot2grid((num, 9),(prev, 0), rowspan=len(result),
                                     colspan=4))
        dendrogram(clust, orientation='right',
                   labels=[tad_names[c] for c in clusters[i]])
        if xlim[0] < axes[-1].get_xlim()[0]:
            xlim[0] = axes[-1].get_xlim()[0]
        if xlim[1] > axes[-1].get_xlim()[1]:
            xlim[1] = axes[-1].get_xlim()[1]
        prev += len(result)
    for ax in axes:
        ax.set_xlim(left=xlim[0], right=xlim[1])
    axes = []
    for i, j in enumerate(dendros):
        axes.append(plt.subplot2grid((num, 9),(i, 4)))#gs1[i]))
        chrom.visualize('exp1',
                        tad=chrom.get_experiment('exp1').tads[tad_names[j]],
                        axe=axes[-1], show=False)
        axes[-1].set_axis_off()
    ax4 = plt.subplot2grid((num, 9),(0, 5), rowspan=num, colspan=4)
    chrom.visualize('exp1', paint_tads=True, axe=ax4)
    plt.draw()


if __name__ == "__main__":
    exit(main())

