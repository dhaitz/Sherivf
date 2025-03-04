#!/usr/bin/env python

"""
Script to calculate the correlation coefficient between PDFs and xs

originally by gsieber
https://gist.github.com/claria/da98570014514f0ada89
"""

import os
import sys
import argparse
import numpy as np

import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gErrorIgnoreLevel = ROOT.kError

import lhapdf
import fastnlo
from fastnlo import fastNLOLHAPDF
lhapdf.setVerbosity(0)


partons = {
    0: 'gluon',
    #-1: 'd antiquark',
    #-2: 'u antiquark',
    #            -3 : 'sbar',
    #            -4 : 'cbar',
    #            -5 : 'bbar',
    #            -6 : 'tbar',
    #1: 'd quark',
    #2: 'u quark',
    #            3 : 'strange',
    #            4 : 'charm',
    #            5 : 'bottom',
    #            6 : 'top',
    7: 'd valence quark',
    8: 'u valence quark',
    9: 'sea quarks',
}


def main():
	#Parse Args
	parser = argparse.ArgumentParser(description='Calculates the correlation coefficient between PDFs and xs')
	parser.add_argument('-t', '--table', help='fastNLO table')
	parser.add_argument('-p', '--pdfset', help='LHAPDF PDF Filename', default='NNPDF30_nlo_as_0118')
	parser.add_argument('-o', '--output-filename', help='corr.root')
	kwargs = vars(parser.parse_args())
	if kwargs['output_filename'] == None:
		kwargs['output_filename'] = os.path.basename(kwargs['table']).replace(".tab", ".root")
	get_corr(**kwargs)


def get_corr(table, pdfset, output_filename, **kwargs):
	storage = get_fnlo(table, pdfset)
	kwargs['table_basename'] = os.path.basename(table)
	x = np.logspace(-4, -0.0001, 250)

	for parton in partons:
		print "calculate correlation for", partons[parton]

		nobsbins = len(storage['xsnlo'])
		obsbins = range(0, nobsbins)
		corr = np.zeros((len(obsbins), len(x)))
		for nobbin, obbin in enumerate(obsbins):
			pdf = get_pdf(pdfset, parton, storage['scale'][nobbin], x)
			for xi in range(0, len(x)):
				corr[nobbin][xi] = np.corrcoef([pdf.transpose()[xi], storage['xsnlo'][obbin]])[0][1]
		y = np.array(list(storage['y_low']) + [storage['y_high'][-1]])
		np_to_root(x, y, corr, partons[parton], output_filename)


def np_to_root(x, y, corr, name, output_filename):
	"""convert np array to root histo, write to file"""
	out = ROOT.TFile(output_filename, "UPDATE")
	tprof = ROOT.TH2D(name, name, len(x)-1, x, len(y)-1, y)

	for ybin, xvalues in enumerate(corr):
		for xbin, xvalue in enumerate(xvalues):
			if not np.isnan(corr[ybin][xbin]):
				tprof.SetBinContent(xbin+1, ybin+1, corr[ybin][xbin])

	tprof.Write()
	out.Close()
	print "written to", output_filename


def get_fnlo(table, pdfset):
	""" Get the cross section values from the table for a certain pdfset"""
	xs_nlo = {}

	fnlo = fastNLOLHAPDF(table)
	fnlo.SetLHAPDFFilename(pdfset)
	fnlo.SetLHAPDFMember(0)
	fnlo.CalcCrossSection()
	npdfmember = fnlo.GetNPDFMembers()

	xs_nlo['xsnlo'] = np.zeros((npdfmember, fnlo.GetNObsBin()))
	xs_nlo['scale'] = np.array(fnlo.GetQScales())

	xs_nlo['y_low'] = [_bin[0] for _bin in fnlo.GetObsBinsBounds(0)]
	xs_nlo['y_high'] = [_bin[1] for _bin in fnlo.GetObsBinsBounds(0)]

	for i in range(npdfmember):
		fnlo.SetLHAPDFMember(i)
		fnlo.CalcCrossSection()
		xs_nlo['xsnlo'][i - 1] = fnlo.GetCrossSection()
	xs_nlo['xsnlo'] = xs_nlo['xsnlo'].transpose()

	return xs_nlo


def get_pdf(pdfset, parton, q, xs):
	"""get the PDF (xfx) for a certain set, parton, x and Q"""

	pdfs = lhapdf.mkPDFs(pdfset)
	pdf = np.zeros((len(pdfs), len(xs)))
	

	for i_member, pdfmember in enumerate(pdfs):
		for (i, xi) in enumerate(xs):
			if parton < 7:
				pdf[i_member - 1][i] = pdfmember.xfxQ(parton, xi, q)
			elif parton == 7:
				#DVAL 1-(-1)
				pdf[i_member - 1][i] = pdfmember.xfxQ(1, xi, q) - \
								 pdfmember.xfxQ(-1, xi, q)
			elif parton == 8:
				#UVAL 2-(-2)
				pdf[i_member - 1][i] = pdfmember.xfxQ(2, xi, q) - \
								 pdfmember.xfxQ(-2, xi, q)
			elif parton == 9:
				#Light sea: xS=2(xubar + xdbar + xsbar)
				pdf[i_member - 1][i] = 2*(pdfmember.xfxQ(-1, xi, q) + \
								 pdfmember.xfxQ(-2, xi, q) + \
								 pdfmember.xfxQ(-3, xi, q))
			else:
				raise ValueError('Parton id not in range 0...9')
	return pdf


if __name__ == '__main__':
	main()
