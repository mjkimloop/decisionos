export type ExtensionContext = {
  trace_id: string;
  config: Record<string, unknown>;
};

export type Hook = (config: Record<string, unknown>, ctx: ExtensionContext) => Promise<Record<string, unknown>> | Record<string, unknown>;

export interface ExtensionHooks {
  pre?: Hook;
  handler: Hook;
  post?: Hook;
}

export function createExtension(hooks: ExtensionHooks) {
  return hooks;
}
