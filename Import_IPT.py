# -*- coding: utf8 -*-

'''
Import_IPT.py:

Simple approach to read/analyse Autodesk (R) Invetor (R) files.
'''

import FreeCAD
import FreeCADGui
import sys
import os
from olefile           import isOleFile, OleFileIO
from importerUtils     import LOG, getInventorFile, setInventorFile, setFileVersion, PrintableName, isEmbeddings, logMessage, logWarning, logError, canImport

__author__      = 'Jens M. Plonka'
__copyright__   = 'Copyright 2017, Germany'
__version__     = '0.6.0'
__status__      = 'In-Development'

# Indicator that everything is ready for the import
from importerReader    import *
from importerFreeCAD   import FreeCADImporter, createGroup

def ReadIgnorable(fname, data):
	logMessage("\t>>> IGNORED: %r" % ('/'.join(fname)))
	logMessage(HexAsciiDump(data), LOG.LOG_DEBUG)
	return len(data)

def skip(data):
	return len(data)

def ReadElement(ole, fname, doc, counter, readProperties):
	end = 0

	name = fname[-1]
	if (len(fname) > 1):
		parent = fname[-2]
	else:
		parent = ''
	path = PrintableName(fname)
	stream = ole.openstream(fname).read()

	folder = getInventorFile()[0:-4]

	if (len(stream)>0):
#		if (name.startswith('\x01') or name.startswith('\x02') or name.startswith('\x05')):
#			binFile = open ('%s\\%s.bin' %(folder, name[1:]), 'wb')
#		else:
#			binFile = open ('%s\\%s.bin' %(folder, name), 'wb')
#			binFile.write(stream)
#			binFile.close()

		if (len(fname) == 1):
			if (name.startswith('\x05')):
				if (readProperties):
					logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
					if (name == '\x05Aaalpg0m0wzvuhc41dwauxbwJc'):
						ReadInventorDocumentSummaryInformation(doc, ole.getproperties(fname, convert_time=True), fname)
					elif (name == '\x05Zrxrt4arFafyu34gYa3l3ohgHg'):
						ReadInventorSummaryInformation(doc, ole.getproperties(fname, convert_time=True), fname)
					else:
						ReadOtherProperties(ole.getproperties(fname, convert_time=True), fname)
				end = len(stream)
			elif (name == 'UFRxDoc'):
				logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
				end = ReadUFRxDoc(stream)
			elif (name == 'Protein'):
				logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
				end = ReadProtein(stream)
			else:
				logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
				end = ReadIgnorable(fname, stream)
		elif (fname[0]=='CacheGraphics'):
			end = skip(stream)
		elif (fname[0]=='RSeStorage'):
			if (isEmbeddings(fname)):
				if (name.startswith('\x05')):
					logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
					# ReadOtherProperties(ole.getproperties(fname, convert_time=True), fname)
					end = skip(stream)
				elif (name == '\x01Ole'):
					logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
#					end = ReadRSeEmbeddingsOle(stream)
					end = skip(stream)
				elif (name == '\x01CompObj'):
					logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
					end = ReadRSeEmbeddingsCompObj(stream)
				elif (name == 'DatabaseInterfaces'):
					logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
					end = ReadRSeEmbeddingsDatabaseInterfaces(stream)
				elif (name == 'Contents'):
#					end = ReadRSeEmbeddingsContents(stream)
					end = skip(stream)
				elif (name == 'Workbook'):
					logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
					end = ReadWorkbook(doc, stream, fname[-2], name)
				else:
					logMessage("%2d: %s" % (counter, path))
					end = ReadIgnorable(fname, stream)
			else:
				if (name == 'RSeDb'):
					logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
					end = ReadRSeDb(stream)
				elif (name == 'RSeSegInfo'):
					logMessage("%2d: %s" % (counter, path))
					if ((model) and (model.RSeDb) and (model.RSeDb.version == 0x1D)):
						end = ReadRSeSegInfo1D(stream)
					else:
						end = ReadRSeSegInfo1F(stream)
				elif (name == 'RSeDbRevisionInfo'):
					logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
					end = ReadRSeDbRevisionInfo(stream)
				elif (name.startswith('B')):
					# Skip! will be handled in 'M'
					end = skip(stream)
				elif (name.startswith('M')):
					logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
					fnameB = []
					for n in (fname):
						fnameB.append(n)
					fnameB[-1] = 'B' + name[1:]
					seg, end = ReadRSeMetaDataM(stream, name[1:])
					dataB = ole.openstream(fnameB).read()
					ReadRSeMetaDataB(dataB, seg)
				else:
					logMessage("%2d: %s" % (counter, path), LOG.LOG_DEBUG)
					end = ReadIgnorable(fname, stream)
		else:
			logMessage("'%2d: %s" % (counter, path), LOG.LOG_DEBUG)
			end = ReadIgnorable(fname, stream)

	return

def ListElement(ole, fname, counter):
	name = fname[-1]

	path = PrintableName(fname)
	stream = ole.openstream(fname).read()
	logMessage("%2d: %s size=%s" % (counter, path, len(stream)), LOG.LOG_ALWAYS)

def ReadFile(doc, readProperties):
	first = 0
	list = {}
	counters = {}

	# LOG.LOG_FILTER = LOG.LOG_FILTER | LOG.LOG_DEBUG

	if (isOleFile(getInventorFile())):
		ole = OleFileIO(getInventorFile())
		setFileVersion(ole)
		elements = ole.listdir(streams=True, storages=False)

		folder = getInventorFile()[0:-4]
		if not os.path.exists(folder):
			os.makedirs(folder)

		counter = 1
		list = []
		for fname in elements:
			if (len(fname) == 1):
				list.append(fname)
			else:
				#Ensure that RSe* files will be parsed first
				if (fname[-1].startswith('RSe')):
					#ensure RSeDb is the very first "file" to be parsed
					list.insert(first, fname)
					if (fname[-1] == 'RSeDb'):
						first += 1
				elif (not fname[-1].startswith('B')):
					list.append(fname)

		for fname in list:
			ReadElement(ole, fname, doc, counter, readProperties)
			counter += 1
		ole.close()

		now = datetime.datetime.now()
		if (len(doc.Comment) > 0):
			doc.Comment += '\n'
		doc.Comment = '# %s: read from %s' %(now.strftime('%Y-%m-%d %H:%M:%S'), getInventorFile())

		logMessage("Dumped data to folder: '%s'" %(getInventorFile()[0:-4]), LOG.LOG_INFO)

		return True
	logError("Error - '%s' is not a valid Autodesk Inventor file." %(infile))
	return False

def insertGroup(doc, filename):
	grpName = os.path.splitext(os.path.basename(filename))[0]
	#There's a problem with adding groups starting with numbers!
	root = createGroup(doc, '_%s' %(grpName))
	root.Label = grpName

	return root

def create3dModel(root, doc):
	global model

	creator = FreeCADImporter(root, doc)
	creator.importModel(model)

	if (FreeCAD.GuiUp):
		FreeCADGui.getDocument(doc.Name).activeView().viewAxonometric()
		FreeCADGui.SendMsgToActiveView("ViewFit")
		logMessage("DONE!", LOG.LOG_ALWAYS)

	return

def insert(filename, docname, skip = [], only = [], root = None):
	'''
	opens an Autodesk Inventor file in the current document
	'''
	if (canImport()):
		try:
			doc = FreeCAD.getDocument(docname)
			logMessage("Importing: %s" %(filename), LOG.LOG_ALWAYS)
			setInventorFile(filename)

			if (ReadFile(doc, False)):
				group = insertGroup(doc, filename)
				create3dModel(group, doc)
		except:
			open(filename, skip, only, root)

	return

def open(filename, skip = [], only = [], root = None):
	'''
	opens an Autodesk Inventor file in a new document
	In addition to insert (import), the iProperties are as well added to the document.
	'''
	if (canImport()):
		logMessage("Reading: %s" %(filename), LOG.LOG_ALWAYS)
		setInventorFile(filename)
		docname = os.path.splitext(os.path.basename(filename))[0]
		docname = decode(docname, utf=True)
		doc = FreeCAD.newDocument(docname)
		doc.Label = docname

		if (ReadFile(doc, True)):
			group = None # Don't create 3D-Model in sub-group
			create3dModel(group, doc)
	return

if __name__ == '__main__':
	if (len(sys.argv) > 1):
		files = sys.argv[1:]
		filename = files[0].decode(sys.getfilesystemencoding()) # make it UNICODE!
		setInventorFile(filename)
		if (isOleFile(filename)):
			if (len(files) == 1):
				open(filename)
			else:
				# this is only for debugging purposes...
				docname = os.path.splitext(os.path.basename(filename))[0]
				docname = decode(docname, utf=True)
				doc = FreeCAD.newDocument(docname)

				ole = OleFileIO(filename)
				setFileVersion(ole)
				elements = ole.listdir(streams=True, storages=False)
				counter = 1
				if (files[1] == 'l'):
					for filename in elements:
						ListElement(ole, filename, counter)
						counter += 1
				else:
					list     = {}
					counters = {}

					for a in (elements):
						path = PrintableName(a)
						list['%s' %(counter)] = a
						counters['%s' %(counter)] = counter
						counter += 1

					for a in (files[1:]):
						if (a in list):
							filename = list[a]
							ReadElement(ole, filename, doc, counters[a], readProperties)
						else:
							p = re.compile(a)
							counter = 1
							for fname in elements:
								if (p.match(PrintableName(fname))):
									ReadElement(ole, filename, doc, counter, readProperties)
						counter += 1

