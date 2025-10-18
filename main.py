from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "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"
)

messages = []

print("Chat started! Type 'exit' or 'quit' to end the conversation.\n")

while True:
    prompt = input("You: ")
    
    if prompt.lower() in ['exit', 'quit']:
        print("Goodbye!")
        break
    
    if not prompt.strip():
        continue
    
    messages.append({"role": "user", "content": prompt})
    
    completion = client.chat.completions.create(
      model="meta/llama-3.2-3b-instruct",
      messages=messages,
      temperature=0.2,
      top_p=0.7,
      max_tokens=1024,
      stream=True
    )
    
    print("AI: ", end="")
    assistant_message = ""
    for chunk in completion:
      if chunk.choices[0].delta.content is not None:
        content = chunk.choices[0].delta.content
        print(content, end="")
        assistant_message += content
    
    print("\n")
    messages.append({"role": "assistant", "content": assistant_message})
