import { StellaSettings } from '../types';
import { LLMProvider, ProviderContext, StreamCallbacks } from './types';

export class LMStudioProvider implements LLMProvider {
    name = 'lmstudio';

    isConfigured(settings: StellaSettings): boolean {
        return !!settings.lmStudioBaseUrl;
    }

    async call(context: ProviderContext): Promise<string> {
        const { settings, messages } = context;

        const response = await fetch(`${settings.lmStudioBaseUrl}/v1/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: settings.model,
                messages: messages,
                max_tokens: settings.maxTokens,
                temperature: settings.temperature
            })
        });

        if (!response.ok) {
            throw new Error(`LM Studio API error: ${response.statusText}`);
        }

        const data = await response.json();
        return data.choices[0].message.content;
    }

    async stream(context: ProviderContext, callbacks: StreamCallbacks): Promise<void> {
        // Fallback: simulate streaming from regular call
        const response = await this.call(context);
        const words = response.split(' ');

        for (let i = 0; i < words.length; i++) {
            const chunk = i === 0 ? words[i] : ' ' + words[i];
            callbacks.onContent(chunk);
            await new Promise(resolve => setTimeout(resolve, 50));
        }

        await callbacks.onComplete();
    }
}
