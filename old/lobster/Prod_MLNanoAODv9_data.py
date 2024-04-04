# Auto generated configuration file
# using: 
# Revision: 1.19 
# Source: /local/reps/CMSSW/CMSSW/Configuration/Applications/python/ConfigBuilder.py,v 
# with command line options: NANO -s NANO --data --conditions 106X_dataRun2_v35 --era Run2_2018 --eventcontent NANOAOD --datatier NANOAOD --customise_commands=process.add_(cms.Service('InitRootHandlers', EnableIMT = cms.untracked.bool(False)));process.MessageLogger.cerr.FwkReport.reportEvery=1000 -n -1 --no_exec
import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

from Configuration.Eras.Era_Run2_2018_cff import Run2_2018

# Command line options
options = VarParsing('analysis')
options.register('year',
                 '2018',
                 VarParsing.multiplicity.singleton,
                 VarParsing.varType.string,
                 'Year to process')

options.parseArguments()

inputFiles = options.inputFiles
outputFile = options.outputFile
maxEvents = options.maxEvents

print('In MLNANOAODv9 maxEvents: {}'.format(maxEvents))

# Process
process = cms.Process('MLNANO',Run2_2018)

# import of standard configurations
process.load('Configuration.StandardSequences.Services_cff')
process.load('SimGeneral.HepPDTESSource.pythiapdt_cfi')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.load('Configuration.EventContent.EventContent_cff')
process.load('Configuration.StandardSequences.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_AutoFromDBCurrent_cff')
process.load('PhysicsTools.NanoAOD.nano_cff')
process.load('Configuration.StandardSequences.EndOfProcess_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_cff')

process.maxEvents = cms.untracked.PSet(
    input = cms.untracked.int32(maxEvents)
)

# Input source
process.source = cms.Source("PoolSource",
    fileNames = cms.untracked.vstring(*inputFiles),
    secondaryFileNames = cms.untracked.vstring()
)

process.options = cms.untracked.PSet()

# Production Info
process.configurationMetadata = cms.untracked.PSet(
    annotation = cms.untracked.string('MLNANO nevts:{}'.format(maxEvents)),
    name = cms.untracked.string('Applications'),
    version = cms.untracked.string('$Revision: 1.19 $')
)

# ML photons #TODO move this stuff to a cff file to reduce duplication
process.diphotons = cms.EDProducer("MLDiphotonProducer",
    collectionLabel = cms.string("diphotons"),
    classifierPath = cms.string("RecoEgamma/EgammaMLDiphotonProducers/data/classifier.onnx"),
    regressorPath = cms.string("RecoEgamma/EgammaMLDiphotonProducers/data/regressor.onnx"),
    clusterInputTag = cms.InputTag('reducedEgamma', 'reducedEBEEClusters', 'PAT'),
    HEEInputTag = cms.InputTag('reducedEgamma', 'reducedEERecHits', 'PAT'),
    HEBInputTag = cms.InputTag('reducedEgamma', 'reducedEBRecHits', 'PAT'),
    pfcandInputTag = cms.InputTag('packedPFCandidates', '', 'PAT'),
    vtxInputTag = cms.InputTag('offlineSlimmedPrimaryVertices', '', 'PAT'),
    pfCandInputTag = cms.InputTag('packedPFCandidates', '', 'PAT')
)

# Define the MLDiphotonsTable module
from PhysicsTools.NanoAOD.common_cff import Var
process.MLDiphotonsTable = cms.EDProducer(
    'SimpleCandidateFlatTableProducer',
    src = cms.InputTag('diphotons', 'diphotons'),
    name = cms.string('MLDiphoton'),
    doc = cms.string('Diphoton Objects and Tagging Variables'),
    singleton = cms.bool(False), # the number of entries is variable
    cut = cms.string(''),
    variables = cms.PSet(
        pt = Var("pt", float, precision=-1),
        eta = Var("eta", float, precision=12),
        phi = Var("phi", float, precision=12),
        massEnergyRatio = Var("massEnergyRatio()", float, doc="Regressed mass/energy"),
        diphotonScore = Var("diphotonScore()", float, doc="Diphoton Classifier score"),
        monophotonScore = Var("monophotonScore()", float, doc="Single Photon Classifier score"),
        hadronScore = Var("hadronScore()", float, doc="Hadronic Classifier score"),
        pfIsolation = Var("pfIsolation()", float, doc="Ratio of diphoton energy to sum of PF candidates energy in a cone of 0.3 around the diphoton)"),
        r1 = Var("r1()", float, doc="IDK"),
        r2 = Var("r2()", float, doc="IDK"),
        r3 = Var("r3()", float, doc="IDK"),
    ),
)

# Output definition

process.NANOAODoutput = cms.OutputModule("NanoAODOutputModule",
    compressionAlgorithm = cms.untracked.string('LZMA'),
    compressionLevel = cms.untracked.int32(9),
    dataset = cms.untracked.PSet(
        dataTier = cms.untracked.string('NANOAOD'),
        filterName = cms.untracked.string('')
    ),
    fileName = cms.untracked.string(outputFile),
    outputCommands = process.NANOAODEventContent.outputCommands
)

# Additional output definition

# Other statements
from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, '106X_dataRun2_v35', '')

# Path and EndPath definitions
process.MLDiphotons_step = cms.Path(process.diphotons)
process.MLDiphotonsTable_step = cms.Path(process.MLDiphotonsTable)
process.nanoAOD_step = cms.Path(process.nanoSequence)
process.endjob_step = cms.EndPath(process.endOfProcess)
process.NANOAODoutput_step = cms.EndPath(process.NANOAODoutput)

# Schedule definition
process.schedule = cms.Schedule(
    process.MLDiphotons_step,
    process.MLDiphotonsTable_step,
    process.nanoAOD_step,
    process.endjob_step,
    process.NANOAODoutput_step
)

from PhysicsTools.PatAlgos.tools.helpers import associatePatAlgosToolsTask
associatePatAlgosToolsTask(process)

# customisation of the process.

# Automatic addition of the customisation function from PhysicsTools.NanoAOD.nano_cff
from PhysicsTools.NanoAOD.nano_cff import nanoAOD_customizeData 

#call to customisation function nanoAOD_customizeData imported from PhysicsTools.NanoAOD.nano_cff
process = nanoAOD_customizeData(process)

# End of customisation functions

# Customisation from command line

process.add_(cms.Service('InitRootHandlers', EnableIMT = cms.untracked.bool(False)));process.MessageLogger.cerr.FwkReport.reportEvery=1000
# Add early deletion of temporary data products to reduce peak memory need
from Configuration.StandardSequences.earlyDeleteSettings_cff import customiseEarlyDelete
process = customiseEarlyDelete(process)
# End adding early deletion
