##################################

setting up ai studio 

nvim ~/.bashrc

then add your api key 

export GEMINI_API_KEY="paste-your-actual-key-here"

source ~/.bashrc


then 

return {
  "olimorris/codecompanion.nvim",
  dependencies = {
    "nvim-lua/plenary.nvim",
    "nvim-treesitter/nvim-treesitter",
    "nvim-telescope/telescope.nvim",
  },
  cmd = { "CodeCompanion", "CodeCompanionChat", "CodeCompanionActions" },
  keys = {
    { "<leader>ai", "<cmd>CodeCompanionChat Toggle<cr>", desc = "Toggle AI Chat" },
    { "<leader>aa", "<cmd>CodeCompanionActions<cr>", mode = { "n", "v" }, desc = "AI Actions" },
  },
  opts = {
    adapters = {
      gemini = function()
        return require("codecompanion.adapters").extend("gemini", {
          env = {
            api_key = "cmd:echo $GEMINI_API_KEY",
          },
        })
      end,
    },
    strategies = {
      chat = { adapter = "gemini" },
      inline = { adapter = "gemini" },
    },
  },
}



to use open nvim and do space a i 



