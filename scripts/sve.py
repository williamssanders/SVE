#!/usr/bin/env python
#BAM input metacalling pipeline
#given a reference directory (same name as the refrence) that already contains all of the
#preprossesing steps such as indexing, masking, chrom spliting, etc...

#simple_sve.py ref_path bam_path out_dir
import os
import sys
import glob
import socket
import time
relink = os.path.dirname(os.path.abspath(__file__))+'/../'
sys.path.append(relink) #go up one in the modules
import stage
import subprocess32 as subprocess
from stages.utils.ParseParameters import ParseParameters
from stages.utils.ParseParameters import para_dict


def Dedup_Sort(in_bam, mem, threads):
    # Mark duplications
    st = stage.Stage('picard_mark_duplicates',dbc)
    dedup_bam = st.run(run_id,{'.bam':in_bam,'mem':mem})
    if (dedup_bam == False):
        print "ERROR: picard_mark_duplicates fails"
    else:
        subprocess.call(["mv",dedup_bam,in_bam])
        # Sort bam
        st = stage.Stage('sambamba_index',dbc)
        st.run(run_id,{'.bam':[in_bam],'threads':threads})

if __name__ == '__main__':
    paras = para_dict
    ParseParameters(paras)

paras['machine'] = socket.gethostname
dbc = {'srv':'','db':'','uid':'','pwd':''}
run_id = 0

if paras['command'] == "align":
    # Index FASTA if they are not there
    if not all ([os.path.isfile(paras['ref'] + '.' + suffix) for suffix in ['amb','ann','bwt','pac','sa']]):
        st = stage.Stage('bwa_index',dbc)
        st.run(run_id, {'.fa':[paras['ref']]})
    # Align
    a_start = time.time()
    aligner_params = {'.fa':paras['ref'],'.fq':paras['FASTQ'],'out_dir':paras['out_dir'],'out_file':paras['out_file'],'threads':paras['threads'],'mem':paras['mem'],'RG':paras['RG']}
    if paras['algorithm'] == 'bwa_mem':
        st = stage.Stage('fq_to_bam_piped',dbc)
        # outs will receive ".sorted.bam"
        sorted_bam = st.run(run_id,aligner_params)
        Dedup_Sort(sorted_bam, paras['mem'], paras['threads'])
    elif paras['algorithm'] == 'speed_seq':
        st = stage.Stage('speedseq_align',dbc)
        outs = st.run(run_id,aligner_params)
    elif paras['algorithm'] == 'bwa_aln':
        st = stage.Stage('bwa_aln',dbc)
        # outs will receive ".sorted.bam"
        sorted_bam = st.run(run_id,aligner_params)
        Dedup_Sort(sorted_bam, paras['mem'], paras['threads'])
    a_stop = time.time()
    print('SVE:BAM:%s was completed in %s hours'%(paras['algorithm'],round((a_stop-a_start)/(60.0**2),4)))

elif paras['command'] == "realign":
    # Index FASTA if they are not there
    if not all ([os.path.isfile(paras['ref'] + '.' + suffix) for suffix in ['amb','ann','bwt','pac','sa']]):
        st = stage.Stage('bwa_index',dbc)
        st.run(run_id, {'.fa':[paras['ref']]})
    # Realign
    a_start = time.time()
    st = stage.Stage('speedseq_realign',dbc)
    outs = st.run(run_id, {'.fa':paras['ref'],'.bam':paras['BAM'][0],'out_dir':paras['out_dir'],'threads':paras['threads'],'mem':paras['mem'],'RG':paras['RG']})
    a_stop = time.time()
    print('SVE:realignment time was % hours'%round((a_stop-a_start)/(60**2),1))

elif paras['command'] == "hg38fix":
    a_start = time.time()
    st = stage.Stage('bwa_hg38_alt_fix',dbc)
    st.run(run_id, {'.bam':paras['BAM'][0],'out_file':paras['out_file']})
    a_stop = time.time()
    print('SVE:hg38fix time was % hours'%round((a_stop-a_start)/(60**2),1))

elif paras['command'] == "call":
    # Please note that some calls are able to take multiple bams for joint calling.
    call_params = {'.fa':paras['ref'],'.bam':paras['BAM'],'out_dir':paras['out_dir'],'threads':paras['threads'],'mem':paras['mem']}
    if paras['algorithm'] == 'genome_strip':
        call_params['genome'] = paras['genome']
        st = stage.Stage('genome_strip_prepare_ref',dbc)
        gs_ref = st.run(run_id, call_params)
        if gs_ref is None: exit()
        call_params['.fa'] = gs_ref['.fa']
        call_params['.svmask.fasta']   = gs_ref['.svmask.fasta']
        call_params['.ploidymap.txt']  = gs_ref['.ploidymap.txt']
        call_params['.rdmask.bed']     = gs_ref['.rdmask.bed']
        call_params['.gendermask.bed'] = gs_ref['.gendermask.bed']
        call_params['.gcmask.fasta']   = gs_ref['.gcmask.fasta']
        call_params['bundle_dir']      = gs_ref['bundle_dir']
        st = stage.Stage('genome_strip',dbc)
        st.run(run_id, call_params)
    if paras['algorithm'] == 'tigra':
	call_params['.vcf'] = paras['vcf']
	st = stage.Stage('tigra',dbc)
        st.run(run_id, call_params)
    if paras['algorithm'] in ['cnvnator', 'lumpy', 'cnmops', 'hydra', 'breakdancer']:
        st = stage.Stage(paras['algorithm'],dbc)
        st.run(run_id, call_params)
    if paras['algorithm'] in ['delly', 'breakseq']:
        call_params['genome'] = paras['genome']
        st = stage.Stage(paras['algorithm'],dbc)
        st.run(run_id, call_params)
