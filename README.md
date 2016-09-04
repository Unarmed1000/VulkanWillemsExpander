# VulkanWillemsExpander
Quick python script to help make the Vulkan source examples from https://github.com/SaschaWillems/Vulkan more verbose
It basically transform most of vkTools::initializers:: to their native vulkan counter part. 
This is useful if you are trying to recreate the samples directly in native vulkan.

Example if the source code reads:

		VkPipelineDynamicStateCreateInfo dynamicState =
			vkTools::initializers::pipelineDynamicStateCreateInfo(
				dynamicStateEnables.data(),
				static_cast<uint32_t>(dynamicStateEnables.size()),
				0);

 This is replaced with:

		VkPipelineDynamicStateCreateInfo dynamicState{};
		dynamicState.sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO;
		dynamicState.flags = 0;
		dynamicState.dynamicStateCount = static_cast<uint32_t>(dynamicStateEnables.size());
		dynamicState.pDynamicStates = dynamicStateEnables.data();

Which size wise is about the same but more applicable for native vulkan development
