/**
 * Incremental parser for the server-sent events streamed by the /chat endpoint.
 * Network chunks can split events at any point, so incomplete text is buffered until the next chunk.
 *
 * @param {(event: string, data: object) => void} onEvent called once per complete event.
 * @returns {(chunk: string) => void} function to feed decoded text chunks into.
 */
export function createSseParser(onEvent) {
  let buffer = "";

  return (chunk) => {
    buffer += chunk.replace(/\r\n/g, "\n");
    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let event = "message";
      const dataLines = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
      }
      if (dataLines.length === 0) continue;

      try {
        onEvent(event, JSON.parse(dataLines.join("\n")));
      } catch (error) {
        console.error("Invalid event from the chatbot API: ", error);
      }
    }
  };
}
