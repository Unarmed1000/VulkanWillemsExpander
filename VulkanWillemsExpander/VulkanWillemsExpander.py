#***************************************************************************************************************************************************
#* BSD 3-Clause License
#*
#* Copyright (c) 2016, Rene Thrane
#* All rights reserved.
#* 
#* Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#* 
#* 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#* 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the 
#*    documentation and/or other materials provided with the distribution.
#* 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this 
#*    software without specific prior written permission.
#* 
#* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
#* THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
#* CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
#* PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF 
#* LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
#* EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#***************************************************************************************************************************************************

# Quick python script to help make the Vulkan source examples from https://github.com/SaschaWillems/Vulkan more verbose
# It basically transform most of vkTools::initializers:: to their native vulkan counter part. 
# This is useful if you are trying to recreate the samples directly in native vulkan.
#
# Example if the source code reads:
#
#		VkPipelineDynamicStateCreateInfo dynamicState =
#			vkTools::initializers::pipelineDynamicStateCreateInfo(
#				dynamicStateEnables.data(),
#				static_cast<uint32_t>(dynamicStateEnables.size()),
#				0);
#
# This is replaced with:
#
#		VkPipelineDynamicStateCreateInfo dynamicState{};
#		dynamicState.sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO;
#		dynamicState.flags = 0;
#		dynamicState.dynamicStateCount = static_cast<uint32_t>(dynamicStateEnables.size());
#		dynamicState.pDynamicStates = dynamicStateEnables.data();
#
# Which size wise is about the same but more applicable for native vulkan development
#

import argparse
import os
from Util import IOUtil

__g_verbosityLevel = 0
__g_debugEnabled = False
__g_allowDevelopmentPlugins = False


def GetTitle():
    return 'VulkanWillemsExpander V0.0.1 alpha'


def ShowTitleIfNecessary():
    global __g_verbosityLevel
    if __g_verbosityLevel > 0:
        print(GetTitle())


class MethodInfo(object):
    def __init__(self, name, parameterCount, expansionParameters):
        super(MethodInfo, self).__init__()
        self.Name = name
        self.ParameterCount = parameterCount
        self.ExpansionParameters = expansionParameters
        self.__Validate(expansionParameters, parameterCount)
    
    def __Validate(self, expansionParameters, parameterCount):
        lookup = set()
        for param in expansionParameters:
            str = param[1]
            if str.startswith("#"):
                str = str[1:]
                paramIndex = int(str)
                if paramIndex < 0 or paramIndex >= len(expansionParameters):
                    raise Exception("Param lookup out of bounds");
                if paramIndex in lookup:
                    raise Exception("Param defined multiple times");
                lookup.add(paramIndex)
        if len(lookup) < parameterCount or len(lookup) > parameterCount:
            raise Exception("incorrect param lookup");



class UseCase:
  Initializer = 0
  FunctionParameter = 1
  ArrayParameter = 2
  ArrayAssignment = 3,
  MemberAssignment = 4,
  Unknown = 5


def ToUseCaseString(value):
    if value == UseCase.Initializer:
        return "Initializer"
    elif value == UseCase.FunctionParameter:
        return "FunctionParameter"
    elif value == UseCase.ArrayParameter:
        return "ArrayParameter"
    return "Unknown"


class SourceEntry(object):
    def __init__(self, startIndex, endIndex, name):
        super(SourceEntry, self).__init__()
        self.StartIndex = startIndex
        self.EndIndex = endIndex
        self.Name = name


class InitRecord(SourceEntry):
    def __init__(self, startIndex, endIndex, name, parameters):
        super(InitRecord, self).__init__(startIndex, endIndex, name)
        self.Parameters = parameters
        self.UseCase = UseCase.Unknown
        self.MethodInfo = None


class VariableNameRecord(SourceEntry):
    def __init__(self, startIndex, endIndex, name):
        super(VariableNameRecord, self).__init__(startIndex, endIndex, name)


class VariableTypeRecord(SourceEntry):
    def __init__(self, startIndex, endIndex, name, indent):
        super(VariableTypeRecord, self).__init__(startIndex, endIndex, name)
        self.Indent = indent;


def FindParametersEnd(source, startIndex):
    paramStartCount = 0
    for i in range(startIndex, len(source)):
        if source[i] == '(':
            paramStartCount = paramStartCount + 1
        elif source[i] == ')':
            paramStartCount = paramStartCount - 1
            if paramStartCount <= 0:
                return i
    return -1


def FunctionCallAwareSplit(parameters):
    splitIndices = []
    paramStartCount = 0
    for i in range(0, len(parameters)):
        if parameters[i] == '(':
            paramStartCount = paramStartCount + 1
        elif parameters[i] == ')':
            paramStartCount = paramStartCount - 1
        elif parameters[i] == ',' and paramStartCount == 0:
            splitIndices.append(i)
    splitIndices.append(len(parameters))

    res = []
    prevIndex = 0
    for index in splitIndices:
        res.append(parameters[prevIndex:index].strip())
        prevIndex = index+1
    return res



def ExtractParameters(parameters):
    parameters = parameters.replace("\n", "")
    parameters = parameters.replace("\r", "")
    parameters = parameters.replace("\t", "")
    parameters = FunctionCallAwareSplit(parameters)
    if len(parameters) == 1 and len(parameters[0]) == 0:
        return []
    return parameters


def FindNextInitializer(source, startIndex):
    searchString = "vkTools::initializers::"
    newIndex = source.find(searchString, startIndex)
    if newIndex < 0:
        return None

    indexParamsBegin = source.find("(", newIndex)
    if indexParamsBegin < 0:
        return None

    indexParamsEnd = FindParametersEnd(source, indexParamsBegin)
    if indexParamsEnd < 0:
        return None

    methodName = source[newIndex+len(searchString):indexParamsBegin]
    parameters = source[indexParamsBegin+1:indexParamsEnd]
    parameters = ExtractParameters(parameters)
    return InitRecord(newIndex, indexParamsEnd+1, methodName, parameters)


#
g_methodBufferCreateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO"),
	("pNext", "nullptr"),
]

#
g_methodBufferCreateInfo2 = [
	("sType", "VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO"),
	("pNext", "nullptr"),
	("flags", "0"),
	("size", "#1"),
	("usage", "#0"),
]

#
g_methodBufferMemoryBarrier0 = [
	("sType", "VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER"),
	("pNext", "nullptr"),
]

#
g_methodCommandBufferAllocateInfo3 = [
	("sType", "VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO"),
	("commandPool", "#0"),
	("level", "#1"),
	("commandBufferCount", "#2"),
]

#
g_methodCommandPoolCreateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO"),
]

#
g_methodCommandBufferBeginInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO"),
	("pNext", "nullptr"),
]

#
g_methodCommandBufferInheritanceInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_COMMAND_BUFFER_INHERITANCE_INFO"),
]

#
g_methodComputePipelineCreateInfo2 = [
	("sType", "VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO"),
	("flags", "#1"),
	("layout", "#0"),
]

#
g_methodDescriptorImageInfo3 = [
	("sampler", "#0"),
	("imageView", "#1"),
	("imageLayout", "#2"),
]

#
g_methodDescriptorPoolCreateInfo3 = [
	("sType", "VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO"),
	("pNext", "nullptr"),
	("maxSets", "#2"),
	("poolSizeCount", "#0"),
	("pPoolSizes", "#1"),
]

#
g_methodDescriptorPoolSize2 = [
	("type", "#0"),
	("descriptorCount", "#1"),
]

#
g_methodDescriptorSetLayoutBinding3 = [
	("binding", "#2"),
	("descriptorType", "#0"),
	("descriptorCount", "1"),
	("stageFlags", "#1"),
]

#
g_methodDescriptorSetLayoutBinding4 = [
	("binding", "#2"),
	("descriptorType", "#0"),
	("descriptorCount", "#3"),
	("stageFlags", "#1"),
]

#
g_methodDescriptorSetAllocateInfo3 = [
	("sType", "VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO"),
	("pNext", "nullptr"),
	("descriptorPool", "#0"),
	("descriptorSetCount", "#2"),
	("pSetLayouts", "#1"),
]

#
g_methodDescriptorSetLayoutCreateInfo2 = [
	("sType", "VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO"),
	("pNext", "nullptr"),
	("bindingCount", "#1"),
	("pBindings", "#0"),
]

#
g_methodEventCreateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_EVENT_CREATE_INFO"),
]

#
g_methodFenceCreateInfo1 = [
	("sType", "VK_STRUCTURE_TYPE_FENCE_CREATE_INFO"),
	("flags", "#0"),
]

#
g_methodFramebufferCreateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO"),
	("pNext", "nullptr"),
]

#
g_methodImageCreateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO"),
	("pNext", "nullptr"),
]

#
g_methodImageMemoryBarrier0 = [
    ("sType", "VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER"), 
    ("pNext", "nullptr"), 
    ("srcQueueFamilyIndex","VK_QUEUE_FAMILY_IGNORED"), 
    ("dstQueueFamilyIndex", "VK_QUEUE_FAMILY_IGNORED") 
]

#
g_methodSamplerCreateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO"),
	("pNext", "nullptr"),
]

#
g_methodMemoryAllocateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO"),
	("pNext", "nullptr"),
	("allocationSize", "0"),
	("memoryTypeIndex", "0")
]

#
g_methodMemoryBarrier0 = [
	("sType", "VK_STRUCTURE_TYPE_MEMORY_BARRIER"),
	("pNext", "nullptr"),
]

#
g_methodPipelineColorBlendAttachmentState2 = [
	("blendEnable", "#1"),
	("colorWriteMask", "#0"),
]

#
g_methodPipelineColorBlendStateCreateInfo2 = [
	("sType", "VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO"),
	("pNext", "nullptr"),
	("attachmentCount", "#0"),
	("pAttachments", "#1"),
]

#
g_methodPipelineCreateInfo3 = [
	("sType", "VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO"),
	("pNext", "nullptr"),
	("flags", "#2"),
	("layout", "#0"),
	("renderPass", "#1"),
]

#
g_methodPipelineDepthStencilStateCreateInfo3 = [
	("sType", "VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO"),
	("depthTestEnable", "#0"),
	("depthWriteEnable", "#1"),
	("depthCompareOp", "#2"),
	("front.compareOp", "VK_COMPARE_OP_ALWAYS"),
	("back.compareOp", "VK_COMPARE_OP_ALWAYS"),
]

#
g_methodPipelineDynamicStateCreateInfo3 = [
	("sType", "VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO"),
	("flags", "#2"),
	("dynamicStateCount", "#1"),
	("pDynamicStates", "#0"),
]

#
g_methodPipelineInputAssemblyStateCreateInfo3 = [
	("sType", "VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO"),
	("flags", "#1"),
	("topology", "#0"),
	("primitiveRestartEnable", "#2"),
]

#
g_methodPipelineLayoutCreateInfo2 = [
	("sType", "VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO"),
	("pNext", "nullptr"),
	("setLayoutCount", "#1"),
	("pSetLayouts", "#0"),
]

#
g_methodPipelineMultisampleStateCreateInfo2 = [
	("sType", "VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO"),
	("flags", "#1"),
	("rasterizationSamples", "#0"),
]

#
g_methodPipelineRasterizationStateCreateInfo4 = [
	("sType", "VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO"),
	("flags", "#3"),
	("polygonMode", "#0"),
	("cullMode", "#1"),
	("frontFace", "#2"),
	("depthClampEnable", "VK_FALSE"),
	("lineWidth", "1.0f"),
]

#
g_methodPipelineTessellationStateCreateInfo1 = [
	("sType", "VK_STRUCTURE_TYPE_PIPELINE_TESSELLATION_STATE_CREATE_INFO"),
	("patchControlPoints", "#0"),
]

#
g_methodPipelineVertexInputStateCreateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO"),
	("pNext", "nullptr"),
]

#
g_methodPipelineViewportStateCreateInfo3 = [
	("sType", "VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO"),
	("flags", "#2"),
	("viewportCount", "#0"),
	("scissorCount", "#1"),
]

#
g_methodRect2D4 = [
	("rect2D.offset.x", "#2"),
	("rect2D.offset.y", "#3"),
	("rect2D.extent.width", "#0"),
	("rect2D.extent.height", "#1"),
]

#
g_methodRenderPassBeginInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO"),
	("pNext", "nullptr"),
]

#
g_methodRenderPassCreateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO"),
	("pNext", "nullptr"),
]

#
g_methodSamplerCreateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO"),
	("pNext", "nullptr"),
]

#
g_methodSemaphoreCreateInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO"),
	("pNext", "nullptr"),
	("flags", "0"),
]

#
g_methodSubmitInfo0 = [
	("sType", "VK_STRUCTURE_TYPE_SUBMIT_INFO"),
	("pNext", "nullptr"),
]

#
g_methodViewport4 = [
	("width", "#0"),
	("height", "#1"),
	("minDepth", "#2"),
	("maxDepth", "#3"),
]

#
g_methodVertexInputBindingDescription3 = [
	("binding", "#0"),
	("stride", "#1"),
	("inputRate", "#2"),
]

#
g_methodVertexInputAttributeDescription4 = [
	("location", "#1"),
	("binding", "#0"),
	("format", "#2"),
	("offset", "#3"),
]

#
g_methodWriteDescriptorSet4A = [
	("sType", "VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET"),
	("pNext", "nullptr"),
	("dstSet", "#0"),
	("dstBinding", "#2"),
	("descriptorCount", "1"),
	("descriptorType", "#1"),
	("pBufferInfo", "#3"),
]

#
g_methodWriteDescriptorSet4B = [
	("sType", "VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET"),
	("pNext", "nullptr"),
	("dstSet", "#0"),
	("dstBinding", "#2"),
	("descriptorCount", "1"),
	("descriptorType", "#1"),
	("pImageInfo", "#3"),
]


g_allMethods = [
    
    MethodInfo("bufferCreateInfo", 0, g_methodBufferCreateInfo0),
    MethodInfo("bufferCreateInfo", 2, g_methodBufferCreateInfo2),
    MethodInfo("bufferMemoryBarrier", 0, g_methodBufferMemoryBarrier0),
    MethodInfo("commandBufferAllocateInfo", 3, g_methodCommandBufferAllocateInfo3),
    MethodInfo("commandPoolCreateInfo", 0, g_methodCommandPoolCreateInfo0),
    MethodInfo("commandBufferBeginInfo", 0, g_methodCommandBufferBeginInfo0),
    MethodInfo("commandBufferInheritanceInfo", 0, g_methodCommandBufferInheritanceInfo0),
    MethodInfo("computePipelineCreateInfo", 2, g_methodComputePipelineCreateInfo2),
    MethodInfo("descriptorImageInfo", 3, g_methodDescriptorImageInfo3),
    MethodInfo("descriptorPoolCreateInfo", 3, g_methodDescriptorPoolCreateInfo3),
    MethodInfo("descriptorPoolSize", 2, g_methodDescriptorPoolSize2),
    MethodInfo("descriptorSetAllocateInfo", 3, g_methodDescriptorSetAllocateInfo3),
    MethodInfo("descriptorSetLayoutCreateInfo", 2, g_methodDescriptorSetLayoutCreateInfo2),
    MethodInfo("descriptorSetLayoutBinding", 3, g_methodDescriptorSetLayoutBinding3),
    MethodInfo("descriptorSetLayoutBinding", 4, g_methodDescriptorSetLayoutBinding4),
    MethodInfo("eventCreateInfo", 0, g_methodEventCreateInfo0),
    MethodInfo("fenceCreateInfo", 1, g_methodFenceCreateInfo1),
    MethodInfo("framebufferCreateInfo", 0, g_methodFramebufferCreateInfo0),
    MethodInfo("imageCreateInfo", 0, g_methodImageCreateInfo0),
    MethodInfo("imageMemoryBarrier", 0, g_methodImageMemoryBarrier0),
    MethodInfo("imageViewCreateInfo", 0, g_methodSamplerCreateInfo0),
    MethodInfo("memoryAllocateInfo", 0, g_methodMemoryAllocateInfo0),
    MethodInfo("memoryBarrier", 0, g_methodMemoryBarrier0),
    MethodInfo("pipelineColorBlendAttachmentState", 2, g_methodPipelineColorBlendAttachmentState2),
    MethodInfo("pipelineColorBlendStateCreateInfo", 2, g_methodPipelineColorBlendStateCreateInfo2),
    MethodInfo("pipelineCreateInfo", 3, g_methodPipelineCreateInfo3),
    MethodInfo("pipelineDepthStencilStateCreateInfo", 3, g_methodPipelineDepthStencilStateCreateInfo3),
    MethodInfo("pipelineDynamicStateCreateInfo", 3, g_methodPipelineDynamicStateCreateInfo3),
    MethodInfo("pipelineInputAssemblyStateCreateInfo", 3, g_methodPipelineInputAssemblyStateCreateInfo3),
    MethodInfo("pipelineLayoutCreateInfo", 2, g_methodPipelineLayoutCreateInfo2),
    MethodInfo("pipelineMultisampleStateCreateInfo", 2, g_methodPipelineMultisampleStateCreateInfo2),
    MethodInfo("pipelineRasterizationStateCreateInfo", 4, g_methodPipelineRasterizationStateCreateInfo4),
    MethodInfo("pipelineTessellationStateCreateInfo", 1, g_methodPipelineTessellationStateCreateInfo1),
    MethodInfo("pipelineVertexInputStateCreateInfo", 0, g_methodPipelineVertexInputStateCreateInfo0),
    MethodInfo("pipelineViewportStateCreateInfo", 3, g_methodPipelineViewportStateCreateInfo3),
    MethodInfo("rect2D", 4, g_methodRect2D4),
    MethodInfo("renderPassBeginInfo", 0, g_methodRenderPassBeginInfo0),
    MethodInfo("renderPassCreateInfo", 0, g_methodRenderPassCreateInfo0),
    MethodInfo("samplerCreateInfo", 0, g_methodSamplerCreateInfo0),
    MethodInfo("semaphoreCreateInfo", 0, g_methodSemaphoreCreateInfo0),
    MethodInfo("submitInfo", 0, g_methodSubmitInfo0),
    MethodInfo("vertexInputBindingDescription", 3, g_methodVertexInputBindingDescription3),
    MethodInfo("vertexInputAttributeDescription", 4, g_methodVertexInputAttributeDescription4),
    MethodInfo("viewport", 4, g_methodViewport4),
    MethodInfo("writeDescriptorSet", 4, g_methodWriteDescriptorSet4A),
    MethodInfo("writeDescriptorSet", 4, g_methodWriteDescriptorSet4B),
]


g_ignoreMethods = {
    "pushConstantRange"
}


def BuildCodeReplacementDict():
    dict = {}
    for entry in g_allMethods:
        if not entry.Name in dict:
            dict[entry.Name] = {}
        dictParams = dict[entry.Name]
        if not entry.ParameterCount in dictParams:
            dict[entry.Name][entry.ParameterCount] = entry
        else:
            found = dict[entry.Name][entry.ParameterCount]
            if not type(found) is type([]):
                found = [ found ]
                dict[entry.Name][entry.ParameterCount] = found
            found.append(entry)
    return dict


def FindReplacementMethodInfo(record, replacementDict):
    if not record.Name in replacementDict:
        return None
    dictParams = replacementDict[record.Name]
    if not len(record.Parameters) in dictParams:
        return None
    return dictParams[len(record.Parameters)]


def LastIndexOfNonWhitepace(source, startIndex):
    for i in reversed(range(0, startIndex)):
        if source[i] != ' ' and source[i] != '\t' and source[i] != '\r' and source[i] != '\n':
            return i
    return -1

def IndexOfNonWhitepace(source, startIndex):
    for i in range(startIndex, len(source)):
        if source[i] != ' ' and source[i] != '\t' and source[i] != '\r' and source[i] != '\n':
            return i
    return -1


def LastIndexOfWhitepace(source, startIndex):
    for i in reversed(range(0, startIndex)):
        if source[i] == ' ' or source[i] == '\t' or source[i] == '\r' or source[i] == '\n':
            return i
    return -1


def DetermineIndentString(source, startIndex):
    index = 0
    for i in reversed(range(0, startIndex)):
        if source[i] == '\r' or source[i] == '\n':
            index = i+1
            break
    endIndex = IndexOfNonWhitepace(source, index)
    if endIndex < 0:
        raise Exception("Not found");
    return source[index:endIndex];



def LocateAssignmentVariableName(source, index):
    index = source.rfind('=', 0, index)
    if index < 0:
        raise Exception("Not a assignment");
    endIndex = LastIndexOfNonWhitepace(source, index-1)
    if endIndex < 0:
        raise Exception("Not a assignment");
    endIndex = endIndex + 1
    startIndex = LastIndexOfWhitepace(source, endIndex)
    if startIndex < 0:
        raise Exception("Not a assignment");
    startIndex = startIndex + 1
    name = source[startIndex:endIndex]
    return VariableNameRecord(startIndex, endIndex, name)


def LocateAssignmentVariableType(source, index):
    endIndex = LastIndexOfNonWhitepace(source, index-1)
    if endIndex < 0:
        raise Exception("type not found");
    endIndex = endIndex + 1
    startIndex = LastIndexOfWhitepace(source, endIndex)
    if startIndex < 0:
        raise Exception("type not found");
    startIndex = startIndex + 1
    name = source[startIndex:endIndex]
    indent = DetermineIndentString(source, startIndex);
    return VariableTypeRecord(startIndex, endIndex, name, indent)


def LookupParameter(formatString, parameters):
    if not formatString.startswith("#"):
        return formatString;
    formatString = formatString[1:]
    index = int(formatString)
    return parameters[index]


def IsAssignmentUseCase(useCase):
    return useCase == UseCase.ArrayAssignment or useCase == UseCase.MemberAssignment or useCase == UseCase.Initializer


def DetermineAlternativeEndIndex(source, record, index):
    if IsAssignmentUseCase(record.UseCase):
        semicolonIndex = source.find(';', index)
        if semicolonIndex < 0:
            raise Exception("Could not locate ';'");
        # skip semicolons
        while semicolonIndex < len(source) and source[semicolonIndex] == ';':
            semicolonIndex = semicolonIndex + 1
        return semicolonIndex
    return index


def PatchCodeComment(source, record):
    strIndent = DetermineIndentString(source, record.StartIndex)
    
    strTo = "\n%s// Lookup of initializer '%s'\n" % (strIndent, record.Name)
    if not type(record.MethodInfo) is type([]):
        for entry in record.MethodInfo.ExpansionParameters:
            strTo += "%s// .%s = %s;\n" % (strIndent, entry[0], LookupParameter(entry[1], record.Parameters))
    else:
        for index, methodInfo in enumerate(record.MethodInfo):
            strTo += "%s// Possibility #%s\n" % (strIndent, index)
            for entry in methodInfo.ExpansionParameters:
                strTo += "%s// .%s = %s;\n" % (strIndent,entry[0], LookupParameter(entry[1], record.Parameters))
    if not IsAssignmentUseCase(record.UseCase):
        strTo += strIndent

    alternativeIndex = DetermineAlternativeEndIndex(source, record, record.EndIndex)
    sourceBefore = source[:alternativeIndex]
    sourceAfter = source[alternativeIndex:]
    return sourceBefore + strTo + sourceAfter


def PatchCodeInitializer(source, record):
    variableNameRecord = LocateAssignmentVariableName(source, record.StartIndex)
    variableTypeRecord = LocateAssignmentVariableType(source, variableNameRecord.StartIndex)

    indent = variableTypeRecord.Indent

    strTo = "%s %s{};\n" % (variableTypeRecord.Name, variableNameRecord.Name)
    if not type(record.MethodInfo) is type([]):
        for entry in record.MethodInfo.ExpansionParameters:
            strTo += "%s%s.%s = %s;\n" % (indent, variableNameRecord.Name, entry[0], LookupParameter(entry[1], record.Parameters))
    else:
        return PatchCodeComment(source, record)

#    strFrom = source[variableTypeRecord.StartIndex:record.EndIndex]
#    print("%s\n%s\n\n" % (strFrom, strTo))
    endIndex = DetermineAlternativeEndIndex(source, record, record.EndIndex)
    sourceBefore = source[:variableTypeRecord.StartIndex]
    sourceAfter = source[endIndex:]
    return sourceBefore + strTo + sourceAfter


def PatchCode(source, record):
    if not record.MethodInfo:
        return source

    if record.UseCase == UseCase.Initializer:
        return PatchCodeInitializer(source, record)
    else:
        return PatchCodeComment(source, record)
    return source


def DetermineAssignmentType(source, record, previousIndex, index):
    foundIndex = LastIndexOfNonWhitepace(source, index)
    if foundIndex < 0:
        raise Exception("hmm");
    if source[foundIndex] == ']':
        return UseCase.ArrayAssignment
    firstWhiteSpaceIndex = LastIndexOfWhitepace(source, foundIndex)
    if firstWhiteSpaceIndex < 0:
        raise Exception("hmm");
    left = source[firstWhiteSpaceIndex+1:foundIndex]
    if '.' in left or "->" in left:
        return UseCase.MemberAssignment
    return UseCase.Initializer


def DetermineUseCase(source, record, previousIndex, previousUseCase):
    # This entire method might be too simplistic
    for i in reversed(range(previousIndex, record.StartIndex)):
        if source[i] == '(':
            return UseCase.FunctionParameter
        elif source[i] == '{':
            return UseCase.ArrayParameter
        elif source[i] == '=':
            return DetermineAssignmentType(source, record, previousIndex, i-1)
    if previousUseCase == UseCase.ArrayParameter:
        return UseCase.ArrayParameter
    return UseCase.Unknown


def ProcesssSourceFile(sourceFileName, targetFileName):
    sourceFile = IOUtil.ReadFile(sourceFileName);
    allEntries = []
    record = FindNextInitializer(sourceFile, 0)
    while record != None:
        if not record.Name in g_ignoreMethods:
            allEntries.append(record)
        record = FindNextInitializer(sourceFile, record.EndIndex)

    previousIndex = 0
    previousUseCase = UseCase.Unknown
    for record in allEntries:
        useCase = DetermineUseCase(sourceFile, record, previousIndex, previousUseCase)
        record.UseCase = useCase
        previousIndex = record.EndIndex
        previousUseCase = useCase

    replacementDict = BuildCodeReplacementDict()
    for record in allEntries:
        record.MethodInfo = FindReplacementMethodInfo(record, replacementDict)
        if not record.MethodInfo:
            print("WARNING: No match %s" % record.Name)

    source = sourceFile
    for record in reversed(allEntries):
        source = PatchCode(source, record)
    IOUtil.WriteFileIfChanged(targetFileName, source);

    #for record in allEntries:
    #    print("Method name '%s' params '%s', useCase %s" % (record.Name, record.Parameters, ToUseCaseString(useCase)))


def AddDefaultOptions(parser):
    parser.add_argument('-v', '--verbosity', action='count', default=0, help='Set verbosity level')
    parser.add_argument('--debug', action='store_true',  help='Enable script debugging')
    parser.add_argument('--dev', action='store_true',  help='Allow plugins in development')


def EarlyArgumentParser():
    global __g_verbosityLevel
    global __g_debugEnabled
    global __g_allowDevelopmentPlugins
    ### Parse the initial options this allows us to use the required debug and verbosity levels while 
    ### creating the actual command line argumnets.
    try:
        parser = argparse.ArgumentParser(add_help=False)
        AddDefaultOptions(parser)
        args, unknown = parser.parse_known_args()
        __g_verbosityLevel = args.verbosity
        __g_debugEnabled = True if args.debug else False;
        __g_allowDevelopmentPlugins = True if args.dev else False;
    except (Exception) as ex:
        print("ERROR: %s" % ex.message)
        if __g_debugEnabled:
            raise
        else:
            return False
    return True

def ProcessFile(sourceFileName, targetFileName):
    if not targetFileName:
        dir = IOUtil.GetDirectoryName(sourceFileName)
        file = IOUtil.GetFileNameWithoutExtension(sourceFileName)
        ext = IOUtil.GetFileNameExtension(sourceFileName)
        targetFileName = IOUtil.Join(dir, "%s__expanded__%s" % (file, ext))
    ProcesssSourceFile(sourceFileName, targetFileName)


def IsTarget(file):
    content = IOUtil.ReadFile(file)
    return ("public VulkanExampleBase" in content)


def Process(sourceFileName, targetFileName, args):
    global __g_verbosityLevel
    if not sourceFileName and not args.recursive:
        return

    if not args.recursive:
        ProcessFile(sourceFileName, targetFileName)
    else:
        if not sourceFileName: 
            sourceFileName = IOUtil.NormalizePath(os.getcwd())
        files = IOUtil.GetFilePaths(sourceFileName, ".cpp")
        for file in files:
            if IsTarget(file):
                if( __g_verbosityLevel > 0 ):
                    print("Processing: %s" % (file))
                ProcessFile(file, None)
            else:
                if( __g_verbosityLevel > 1 ):
                    print("Skipping: %s" % (file))



def main():
    global __g_verbosityLevel
    global __g_debugEnabled
    global __g_allowDevelopmentPlugins

    if not EarlyArgumentParser():
        return

    ### Add the main command line arguments
    parser = argparse.ArgumentParser(description='Quick python script to help make the Vulkan source examples from https://github.com/SaschaWillems/Vulkan more verbose.')
    AddDefaultOptions(parser)
    parser.add_argument("inputFile",  nargs='?', help="the name of the input file")
    parser.add_argument("outputFile", nargs='?', default=None, help="the name of the output file")
    parser.add_argument('-r', '--recursive', action='store_true',  help="Scan the given path recursively for .cpp files that contain 'public VulkanExampleBase' and process those that do")

    try:
        args = parser.parse_args()
        Process(args.inputFile, args.outputFile, args)
    except (IOError) as ex:
        ShowTitleIfNecessary()
        print("ERROR: %s" % ex.strerror)
        if __g_debugEnabled:
            raise
    except (Exception) as ex:
        ShowTitleIfNecessary()
        print("ERROR: %s" % ex.message)
        if __g_debugEnabled:
            raise
    return

main()