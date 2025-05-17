graph TD
    subgraph User/External_LLM_Orchestrator
        U[User via Terminal]
        ELO[External LLM Orchestrator]
    end

    subgraph Damien_CLI_Application [Damien-CLI Application]
        DC[damien_cli.py <br> (Click/Typer, Cmd Dispatch)]
        CM[config_manager.py <br> (Settings, API Keys)]
        LOG[logger.py / logging <br> (Action Logging)]

        subgraph Core_Services
            GS[gmail_service.py <br> (Gmail API, Auth, Email Ops)]
            RE[rules_engine.py <br> (Static/Dynamic Rules)]
            LI[llm_interface.py <br> (Internal LLM Calls)]
            AP[analysis_processor.py <br> (Processes LLM/Rule Output)]
            UH[unsubscribe_handler.py <br> (Unsubscribe Logic)]
            SDH[session_data_handler.py <br> (In-memory DB/Data)]
        end

        subgraph Data_Storage [Local Data Storage]
            CSJ[credentials.json <br> (Google Client Secrets)]
            TJ[token.json <br> (Google OAuth Tokens)]
            RJ[rules.json <br> (User-defined Rules)]
            SLOG[damien_session.log <br> (Session Log File)]
            CONF[config.ini / .env <br> (App Config, LLM Keys)]
        end
    end

    subgraph External_Services
        GAPI[Gmail API]
        LLM_API[LLM API <br> (e.g., OpenAI)]
    end

    %% User/Orchestrator Interaction with CLI
    U -->|Executes `damien` commands| DC
    ELO -->|Executes `damien ... --json`| DC

    %% CLI Core Interactions
    DC -->|Reads config| CM
    DC -->|Dispatches to services based on command| GS
    DC -->|Dispatches to services based on command| RE
    DC -->|Dispatches to services based on command| LI
    DC -->|Dispatches to services based on command| AP
    DC -->|Dispatches to services based on command| UH
    DC -->|Uses for complex temp data| SDH
    DC -->|Writes to| LOG

    %% Service Interactions
    GS -->|Authenticates & interacts| GAPI
    GS -->|Reads/Writes| TJ
    GS -->|Reads| CSJ
    RE -->|Reads/Writes rules| RJ
    RE -->|Uses for rule matching| GS %% To get email details for matching
    LI -->|Makes API calls| LLM_API
    LI -->|Reads LLM API keys from| CM
    AP -->|Gets data from| LI
    AP -->|Gets data from| RE %% Could also process results of static rules
    AP -->|Provides actionable plans to| DC %% Which then calls GS to execute
    UH -->|Uses to get email headers| GS
    UH -->|Uses to send unsubscribe email| GS
    SDH -->|Populated by data from| GS

    %% Config Manager used by multiple services
    GS -->|Gets paths/settings| CM
    LOG -->|Gets logging config| CM


    %% Styling (Optional, for clarity)
    classDef user fill:#c9f,stroke:#333,stroke-width:2px;
    classDef cli fill:#f9f,stroke:#333,stroke-width:2px;
    classDef service fill:#9cf,stroke:#333,stroke-width:2px;
    classDef storage fill:#lightgrey,stroke:#333,stroke-width:2px;
    classDef external fill:#9f9,stroke:#333,stroke-width:2px;

    class U,ELO user;
    class DC cli;
    class GS,RE,LI,AP,UH,SDH,CM,LOG service;
    class CSJ,TJ,RJ,SLOG,CONF storage;
    class GAPI,LLM_API external;
```

**Explanation of the Diagram:**

*   **User/External_LLM_Orchestrator (Pinkish Purple):** Represents the actors initiating commands.
    *   `User via Terminal`: Direct interaction.
    *   `External LLM Orchestrator`: Programmatic interaction (if Damien is used as a tool by another LLM system).
*   **Damien_CLI_Application (Purple Box):** The main application.
    *   `damien_cli.py`: The central entry point and command dispatcher.
    *   `config_manager.py` & `logger.py`: Cross-cutting concerns.
    *   **Core_Services (Light Blue Box):** These are the main Python modules handling specific logic:
        *   `gmail_service.py`: All things Gmail API.
        *   `rules_engine.py`: For predefined and LLM-suggested static rules.
        *   `llm_interface.py`: For Damien's *own* calls to LLMs (e.g., for `damien analyze`).
        *   `analysis_processor.py`: Processes outputs from `llm_interface` or `rules_engine` to decide what actions to take (e.g., for `damien clean`).
        *   `unsubscribe_handler.py`: Specific logic for unsubscribe.
        *   `session_data_handler.py`: For managing temporary, in-memory datasets for complex operations.
    *   **Data_Storage (Grey Box):** Represents the files Damien uses to store persistent data or configuration.
*   **External_Services (Green Box):** Services Damien interacts with over the network.
    *   `Gmail API`: For all email operations.
    *   `LLM API`: If Damien's `analyze` command or similar uses an LLM directly.

**Arrows indicate data flow or control flow:**
*   `A --> B`: A sends data to B or calls B.
*   `A -->|description| B`: Adds a description to the interaction.

**How to use this:**
1.  Go to a Mermaid live editor (e.g., `mermaid.live` or the official Mermaid documentation site's editor).
2.  Paste the code block above into the editor.
3.  It will render the diagram.

This diagram should give you a clear visual overview of how the different parts of Damien-CLI are intended to connect and interact. We can refine it further if needed!