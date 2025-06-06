import react from "@vitejs/plugin-react";
import "dotenv/config";
import path from "node:path";
import { defineConfig, splitVendorChunkPlugin } from "vite";
import injectHTML from "vite-plugin-html-inject";
import tsConfigPaths from "vite-tsconfig-paths";

type Extension = {
	name: string;
	version: string;
	config: Record<string, unknown>;
};

enum ExtensionName {
	FIREBASE_AUTH = "firebase-auth",
}

const listExtensions = (): Extension[] => {
	if (process.env.DATABUTTON_EXTENSIONS) {
		try {
			return JSON.parse(process.env.DATABUTTON_EXTENSIONS) as Extension[];
		} catch (err: unknown) {
			console.error("Error parsing DATABUTTON_EXTENSIONS", err);
			console.error(process.env.DATABUTTON_EXTENSIONS);
			return [];
		}
	}

	return [];
};

const extensions = listExtensions();

const getExtensionConfig = (name: string): string => {
	const extension = extensions.find((it) => it.name === name);

	if (!extension) {
		console.warn(`Extension ${name} not found`);
	}

	return JSON.stringify(extension?.config);
};

const buildVariables = () => {
	const appId = process.env.DATABUTTON_PROJECT_ID;

	// Construct Firebase config from VITE_ environment variables
	// These should be set in your frontend/.env file
	const localFirebaseConfig = {
		apiKey: process.env.VITE_FIREBASE_API_KEY || "",
		authDomain: process.env.VITE_FIREBASE_AUTH_DOMAIN || "",
		projectId: process.env.VITE_FIREBASE_PROJECT_ID || "",
		storageBucket: process.env.VITE_FIREBASE_STORAGE_BUCKET || "",
		messagingSenderId: process.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "",
		appId: process.env.VITE_FIREBASE_APP_ID || "",
	};

	// Check if we have local Firebase config, otherwise try Databutton extension
	let fullConfig;
	if (localFirebaseConfig.projectId) {
		// Use local Firebase config with default auth extension config structure
		fullConfig = {
			signInOptions: {
				google: true,
				github: false,
				facebook: false,
				twitter: false,
				emailAndPassword: true,
				magicLink: false,
			},
			siteName: "Databutton", // Matches current __APP_TITLE__
			signInSuccessUrl: "/",
			firebaseConfig: localFirebaseConfig,
		};
	} else {
		// Fallback to Databutton extension config
		const extensionConfigString = getExtensionConfig(ExtensionName.FIREBASE_AUTH);
		// Ensure fullConfig is an object, not a string, before proceeding
		if (extensionConfigString && typeof extensionConfigString === 'string') {
			try {
				fullConfig = JSON.parse(extensionConfigString);
			} catch (e) {
				console.error("vite.config.ts: Error parsing extensionConfigString:", e, extensionConfigString);
				fullConfig = {}; // Default to empty object on parse error
			}
		} else {
			fullConfig = {};
		}

		// Ensure fullConfig is an object and has firebaseConfig
		if (typeof fullConfig !== 'object' || fullConfig === null) {
			fullConfig = {};
		}
		if (!fullConfig.firebaseConfig) {
			console.warn("Firebase config from extension is missing or malformed, defaulting firebaseConfig to empty object.");
			fullConfig.firebaseConfig = {};
		}
	}

	// Ensure fullConfig is definitely an object before stringifying
	if (typeof fullConfig !== 'object' || fullConfig === null) {
		// console.error("vite.config.ts: fullConfig is not an object before final stringify. Forcing to {}.", fullConfig); // Keep if needed for future debug
		fullConfig = {};
	}
	
	const stringifiedConfig = JSON.stringify(fullConfig);
	const base64EncodedConfig = Buffer.from(stringifiedConfig).toString('base64');

	const defines: Record<string, string> = {
		// Inject the Base64 string as a string literal for __FIREBASE_CONFIG_BASE64__
		__FIREBASE_CONFIG_BASE64__: JSON.stringify(base64EncodedConfig),
		__APP_ID__: JSON.stringify(appId),
		__API_PATH__: JSON.stringify(""),
		__API_URL__: JSON.stringify("http://localhost:8000"),
		__WS_API_URL__: JSON.stringify("ws://localhost:8000"),
		__APP_BASE_PATH__: JSON.stringify("/"),
		__APP_TITLE__: JSON.stringify("Databutton"),
		__APP_FAVICON_LIGHT__: JSON.stringify("/favicon-light.svg"),
		__APP_FAVICON_DARK__: JSON.stringify("/favicon-dark.svg"),
		__APP_DEPLOY_USERNAME__: JSON.stringify(""),
		__APP_DEPLOY_APPNAME__: JSON.stringify(""),
		__APP_DEPLOY_CUSTOM_DOMAIN__: JSON.stringify(""),
		// __FIREBASE_CONFIG__: firebaseConfigDefine, // Remove old define
	};

	return defines;
};

// https://vite.dev/config/
export default defineConfig({
	define: buildVariables(),
	plugins: [react(), splitVendorChunkPlugin(), tsConfigPaths(), injectHTML()],
	server: {
		port: 5100, // Set preferred frontend port
		proxy: {
			"/routes": {
				target: "http://127.0.0.1:8123", // Updated to backend port 8123
				changeOrigin: true,
			},
		},
	},
	resolve: {
		alias: {
			resolve: {
				alias: {
					"@": path.resolve(__dirname, "./src"),
				},
			},
		},
	},
});
