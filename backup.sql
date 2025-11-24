--
-- PostgreSQL database dump
--

\restrict JmYhn2ScGNik79RnDLMzbUmzMuzvxfIo0sywinRcHxJehVfssduKAPe9wiGnqgm

-- Dumped from database version 18.0 (Debian 18.0-1.pgdg13+3)
-- Dumped by pg_dump version 18.0 (Debian 18.0-1.pgdg13+3)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: armoires; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.armoires (
    id integer NOT NULL,
    nom character varying NOT NULL,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.armoires OWNER TO postgres;

--
-- Name: armoires_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.armoires_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.armoires_id_seq OWNER TO postgres;

--
-- Name: armoires_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.armoires_id_seq OWNED BY public.armoires.id;


--
-- Name: budgets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.budgets (
    id integer NOT NULL,
    annee integer NOT NULL,
    montant_initial double precision NOT NULL,
    cloture boolean NOT NULL,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.budgets OWNER TO postgres;

--
-- Name: budgets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.budgets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.budgets_id_seq OWNER TO postgres;

--
-- Name: budgets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.budgets_id_seq OWNED BY public.budgets.id;


--
-- Name: categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.categories (
    id integer NOT NULL,
    nom character varying NOT NULL,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.categories OWNER TO postgres;

--
-- Name: categories_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.categories_id_seq OWNER TO postgres;

--
-- Name: categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.categories_id_seq OWNED BY public.categories.id;


--
-- Name: depenses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.depenses (
    id integer NOT NULL,
    budget_id integer NOT NULL,
    fournisseur_id integer,
    contenu text NOT NULL,
    montant double precision NOT NULL,
    date_depense date NOT NULL,
    est_bon_achat boolean NOT NULL,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.depenses OWNER TO postgres;

--
-- Name: depenses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.depenses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.depenses_id_seq OWNER TO postgres;

--
-- Name: depenses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.depenses_id_seq OWNED BY public.depenses.id;


--
-- Name: echeances; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.echeances (
    id integer NOT NULL,
    intitule text NOT NULL,
    date_echeance date NOT NULL,
    details text,
    traite integer NOT NULL,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.echeances OWNER TO postgres;

--
-- Name: echeances_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.echeances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.echeances_id_seq OWNER TO postgres;

--
-- Name: echeances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.echeances_id_seq OWNED BY public.echeances.id;


--
-- Name: etablissements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.etablissements (
    id integer NOT NULL,
    nom character varying NOT NULL,
    ville character varying
);


ALTER TABLE public.etablissements OWNER TO postgres;

--
-- Name: etablissements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.etablissements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.etablissements_id_seq OWNER TO postgres;

--
-- Name: etablissements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.etablissements_id_seq OWNED BY public.etablissements.id;


--
-- Name: fournisseurs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fournisseurs (
    id integer NOT NULL,
    nom character varying NOT NULL,
    site_web character varying,
    logo character varying,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.fournisseurs OWNER TO postgres;

--
-- Name: fournisseurs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.fournisseurs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.fournisseurs_id_seq OWNER TO postgres;

--
-- Name: fournisseurs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.fournisseurs_id_seq OWNED BY public.fournisseurs.id;


--
-- Name: historique; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.historique (
    id integer NOT NULL,
    objet_id integer NOT NULL,
    utilisateur_id integer NOT NULL,
    action character varying NOT NULL,
    details text,
    "timestamp" timestamp without time zone NOT NULL,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.historique OWNER TO postgres;

--
-- Name: historique_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.historique_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.historique_id_seq OWNER TO postgres;

--
-- Name: historique_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.historique_id_seq OWNED BY public.historique.id;


--
-- Name: kit_objets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kit_objets (
    id integer NOT NULL,
    kit_id integer NOT NULL,
    objet_id integer NOT NULL,
    quantite integer NOT NULL,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.kit_objets OWNER TO postgres;

--
-- Name: kit_objets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.kit_objets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kit_objets_id_seq OWNER TO postgres;

--
-- Name: kit_objets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.kit_objets_id_seq OWNED BY public.kit_objets.id;


--
-- Name: kits; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.kits (
    id integer NOT NULL,
    nom character varying NOT NULL,
    description text,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.kits OWNER TO postgres;

--
-- Name: kits_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.kits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.kits_id_seq OWNER TO postgres;

--
-- Name: kits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.kits_id_seq OWNED BY public.kits.id;


--
-- Name: objets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.objets (
    id integer NOT NULL,
    nom character varying NOT NULL,
    quantite_physique integer NOT NULL,
    seuil integer NOT NULL,
    armoire_id integer NOT NULL,
    categorie_id integer NOT NULL,
    en_commande integer NOT NULL,
    date_peremption character varying,
    traite integer NOT NULL,
    image_url character varying,
    fds_url character varying,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.objets OWNER TO postgres;

--
-- Name: objets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.objets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.objets_id_seq OWNER TO postgres;

--
-- Name: objets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.objets_id_seq OWNED BY public.objets.id;


--
-- Name: parametres; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.parametres (
    id integer NOT NULL,
    cle character varying NOT NULL,
    valeur character varying,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.parametres OWNER TO postgres;

--
-- Name: parametres_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.parametres_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.parametres_id_seq OWNER TO postgres;

--
-- Name: parametres_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.parametres_id_seq OWNED BY public.parametres.id;


--
-- Name: reservations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reservations (
    id integer NOT NULL,
    objet_id integer NOT NULL,
    utilisateur_id integer NOT NULL,
    quantite_reservee integer NOT NULL,
    debut_reservation timestamp without time zone NOT NULL,
    fin_reservation timestamp without time zone NOT NULL,
    groupe_id character varying,
    kit_id integer,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.reservations OWNER TO postgres;

--
-- Name: reservations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reservations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reservations_id_seq OWNER TO postgres;

--
-- Name: reservations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reservations_id_seq OWNED BY public.reservations.id;


--
-- Name: utilisateurs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.utilisateurs (
    id integer NOT NULL,
    nom_utilisateur character varying NOT NULL,
    mot_de_passe character varying NOT NULL,
    role character varying NOT NULL,
    email character varying,
    etablissement_id integer NOT NULL
);


ALTER TABLE public.utilisateurs OWNER TO postgres;

--
-- Name: utilisateurs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.utilisateurs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.utilisateurs_id_seq OWNER TO postgres;

--
-- Name: utilisateurs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.utilisateurs_id_seq OWNED BY public.utilisateurs.id;


--
-- Name: armoires id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.armoires ALTER COLUMN id SET DEFAULT nextval('public.armoires_id_seq'::regclass);


--
-- Name: budgets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.budgets ALTER COLUMN id SET DEFAULT nextval('public.budgets_id_seq'::regclass);


--
-- Name: categories id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories ALTER COLUMN id SET DEFAULT nextval('public.categories_id_seq'::regclass);


--
-- Name: depenses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.depenses ALTER COLUMN id SET DEFAULT nextval('public.depenses_id_seq'::regclass);


--
-- Name: echeances id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.echeances ALTER COLUMN id SET DEFAULT nextval('public.echeances_id_seq'::regclass);


--
-- Name: etablissements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.etablissements ALTER COLUMN id SET DEFAULT nextval('public.etablissements_id_seq'::regclass);


--
-- Name: fournisseurs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fournisseurs ALTER COLUMN id SET DEFAULT nextval('public.fournisseurs_id_seq'::regclass);


--
-- Name: historique id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.historique ALTER COLUMN id SET DEFAULT nextval('public.historique_id_seq'::regclass);


--
-- Name: kit_objets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kit_objets ALTER COLUMN id SET DEFAULT nextval('public.kit_objets_id_seq'::regclass);


--
-- Name: kits id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kits ALTER COLUMN id SET DEFAULT nextval('public.kits_id_seq'::regclass);


--
-- Name: objets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objets ALTER COLUMN id SET DEFAULT nextval('public.objets_id_seq'::regclass);


--
-- Name: parametres id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.parametres ALTER COLUMN id SET DEFAULT nextval('public.parametres_id_seq'::regclass);


--
-- Name: reservations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reservations ALTER COLUMN id SET DEFAULT nextval('public.reservations_id_seq'::regclass);


--
-- Name: utilisateurs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utilisateurs ALTER COLUMN id SET DEFAULT nextval('public.utilisateurs_id_seq'::regclass);


--
-- Data for Name: armoires; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.armoires (id, nom, etablissement_id) FROM stdin;
1	Armoire 01	1
2	Armoire 02	1
\.


--
-- Data for Name: budgets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.budgets (id, annee, montant_initial, cloture, etablissement_id) FROM stdin;
1	2025	650	f	1
\.


--
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.categories (id, nom, etablissement_id) FROM stdin;
1	Verrerie	1
2	Dissection	1
\.


--
-- Data for Name: depenses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.depenses (id, budget_id, fournisseur_id, contenu, montant, date_depense, est_bon_achat, etablissement_id) FROM stdin;
1	1	\N	kiwis	3.99	2025-10-30	t	1
\.


--
-- Data for Name: echeances; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.echeances (id, intitule, date_echeance, details, traite, etablissement_id) FROM stdin;
1	Prévoire budget 2026-2027	2025-11-03	None	0	1
\.


--
-- Data for Name: etablissements; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.etablissements (id, nom, ville) FROM stdin;
1	Collège Gabriel Pierné	\N
\.


--
-- Data for Name: fournisseurs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.fournisseurs (id, nom, site_web, logo, etablissement_id) FROM stdin;
1	JEULIN	https://www.jeulin.fr	https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRsAMTnIYkUUgVL6b9ZFfzxvvgP0SqcSf70Wg&s	1
\.


--
-- Data for Name: historique; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.historique (id, objet_id, utilisateur_id, action, details, "timestamp", etablissement_id) FROM stdin;
\.


--
-- Data for Name: kit_objets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.kit_objets (id, kit_id, objet_id, quantite, etablissement_id) FROM stdin;
1	1	1	2	1
\.


--
-- Data for Name: kits; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.kits (id, nom, description, etablissement_id) FROM stdin;
1	Essai		1
\.


--
-- Data for Name: objets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.objets (id, nom, quantite_physique, seuil, armoire_id, categorie_id, en_commande, date_peremption, traite, image_url, fds_url, etablissement_id) FROM stdin;
1	Bécher 110 mL	10	5	1	1	0	\N	0	https://www.chemscience.com/assets/product-images/1659989328259_229_203_07_(1).jpg	\N	1
2	Scalpel	20	10	2	2	0	\N	0	https://encrypted-tbn0.gstatic.com/shopping?q=tbn:ANd9GcRNmQnz3ZorDKBRIi3teE7rdRY39c3dZ2ilmRQDWq7g35TLjGUWHFUgTUdfn0KLZivekJoyKUQajz4UwOc5ti_QfkbtWx5ErXBAiS-bS0v5clyPvN9GgS6fEvO3UorjasJV7EjHFg&usqp=CAc	\N	1
\.


--
-- Data for Name: parametres; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.parametres (id, cle, valeur, etablissement_id) FROM stdin;
1	instance_id	cb035860-8238-4641-bf08-d3bae6537dd7	1
2	licence_statut	FREE	1
3	items_per_page	10	1
\.


--
-- Data for Name: reservations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reservations (id, objet_id, utilisateur_id, quantite_reservee, debut_reservation, fin_reservation, groupe_id, kit_id, etablissement_id) FROM stdin;
\.


--
-- Data for Name: utilisateurs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.utilisateurs (id, nom_utilisateur, mot_de_passe, role, email, etablissement_id) FROM stdin;
1	Admin	scrypt:32768:8:1$k98JNWyEoOxKt20l$9912b2091d6f8cf318be4c90370e093d79d0f761181924fd436fcdd35758a1b455a5918b5852f5d5361b7a853be2090992213203d6499be57e01eb318f68c951	admin	xdebaudry@gmail.com	1
\.


--
-- Name: armoires_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.armoires_id_seq', 2, true);


--
-- Name: budgets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.budgets_id_seq', 1, true);


--
-- Name: categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.categories_id_seq', 2, true);


--
-- Name: depenses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.depenses_id_seq', 1, true);


--
-- Name: echeances_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.echeances_id_seq', 1, true);


--
-- Name: etablissements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.etablissements_id_seq', 1, true);


--
-- Name: fournisseurs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.fournisseurs_id_seq', 1, true);


--
-- Name: historique_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.historique_id_seq', 1, false);


--
-- Name: kit_objets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.kit_objets_id_seq', 2, true);


--
-- Name: kits_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.kits_id_seq', 1, true);


--
-- Name: objets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.objets_id_seq', 2, true);


--
-- Name: parametres_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.parametres_id_seq', 3, true);


--
-- Name: reservations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.reservations_id_seq', 4, true);


--
-- Name: utilisateurs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.utilisateurs_id_seq', 1, true);


--
-- Name: budgets _annee_etablissement_uc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.budgets
    ADD CONSTRAINT _annee_etablissement_uc UNIQUE (annee, etablissement_id);


--
-- Name: armoires armoires_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.armoires
    ADD CONSTRAINT armoires_pkey PRIMARY KEY (id);


--
-- Name: budgets budgets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.budgets
    ADD CONSTRAINT budgets_pkey PRIMARY KEY (id);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: depenses depenses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.depenses
    ADD CONSTRAINT depenses_pkey PRIMARY KEY (id);


--
-- Name: echeances echeances_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.echeances
    ADD CONSTRAINT echeances_pkey PRIMARY KEY (id);


--
-- Name: etablissements etablissements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.etablissements
    ADD CONSTRAINT etablissements_pkey PRIMARY KEY (id);


--
-- Name: fournisseurs fournisseurs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fournisseurs
    ADD CONSTRAINT fournisseurs_pkey PRIMARY KEY (id);


--
-- Name: historique historique_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.historique
    ADD CONSTRAINT historique_pkey PRIMARY KEY (id);


--
-- Name: kit_objets kit_objets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kit_objets
    ADD CONSTRAINT kit_objets_pkey PRIMARY KEY (id);


--
-- Name: kits kits_nom_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kits
    ADD CONSTRAINT kits_nom_key UNIQUE (nom);


--
-- Name: kits kits_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kits
    ADD CONSTRAINT kits_pkey PRIMARY KEY (id);


--
-- Name: objets objets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objets
    ADD CONSTRAINT objets_pkey PRIMARY KEY (id);


--
-- Name: parametres parametres_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.parametres
    ADD CONSTRAINT parametres_pkey PRIMARY KEY (id);


--
-- Name: reservations reservations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_pkey PRIMARY KEY (id);


--
-- Name: utilisateurs utilisateurs_nom_utilisateur_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utilisateurs
    ADD CONSTRAINT utilisateurs_nom_utilisateur_key UNIQUE (nom_utilisateur);


--
-- Name: utilisateurs utilisateurs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utilisateurs
    ADD CONSTRAINT utilisateurs_pkey PRIMARY KEY (id);


--
-- Name: armoires armoires_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.armoires
    ADD CONSTRAINT armoires_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: budgets budgets_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.budgets
    ADD CONSTRAINT budgets_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: categories categories_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: depenses depenses_budget_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.depenses
    ADD CONSTRAINT depenses_budget_id_fkey FOREIGN KEY (budget_id) REFERENCES public.budgets(id);


--
-- Name: depenses depenses_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.depenses
    ADD CONSTRAINT depenses_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: depenses depenses_fournisseur_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.depenses
    ADD CONSTRAINT depenses_fournisseur_id_fkey FOREIGN KEY (fournisseur_id) REFERENCES public.fournisseurs(id);


--
-- Name: echeances echeances_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.echeances
    ADD CONSTRAINT echeances_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: fournisseurs fournisseurs_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fournisseurs
    ADD CONSTRAINT fournisseurs_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: historique historique_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.historique
    ADD CONSTRAINT historique_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: historique historique_objet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.historique
    ADD CONSTRAINT historique_objet_id_fkey FOREIGN KEY (objet_id) REFERENCES public.objets(id) ON DELETE CASCADE;


--
-- Name: historique historique_utilisateur_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.historique
    ADD CONSTRAINT historique_utilisateur_id_fkey FOREIGN KEY (utilisateur_id) REFERENCES public.utilisateurs(id) ON DELETE CASCADE;


--
-- Name: kit_objets kit_objets_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kit_objets
    ADD CONSTRAINT kit_objets_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: kit_objets kit_objets_kit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kit_objets
    ADD CONSTRAINT kit_objets_kit_id_fkey FOREIGN KEY (kit_id) REFERENCES public.kits(id) ON DELETE CASCADE;


--
-- Name: kit_objets kit_objets_objet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kit_objets
    ADD CONSTRAINT kit_objets_objet_id_fkey FOREIGN KEY (objet_id) REFERENCES public.objets(id) ON DELETE CASCADE;


--
-- Name: kits kits_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.kits
    ADD CONSTRAINT kits_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: objets objets_armoire_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objets
    ADD CONSTRAINT objets_armoire_id_fkey FOREIGN KEY (armoire_id) REFERENCES public.armoires(id);


--
-- Name: objets objets_categorie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objets
    ADD CONSTRAINT objets_categorie_id_fkey FOREIGN KEY (categorie_id) REFERENCES public.categories(id);


--
-- Name: objets objets_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.objets
    ADD CONSTRAINT objets_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: parametres parametres_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.parametres
    ADD CONSTRAINT parametres_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: reservations reservations_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- Name: reservations reservations_kit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_kit_id_fkey FOREIGN KEY (kit_id) REFERENCES public.kits(id);


--
-- Name: reservations reservations_objet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_objet_id_fkey FOREIGN KEY (objet_id) REFERENCES public.objets(id);


--
-- Name: reservations reservations_utilisateur_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_utilisateur_id_fkey FOREIGN KEY (utilisateur_id) REFERENCES public.utilisateurs(id);


--
-- Name: utilisateurs utilisateurs_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utilisateurs
    ADD CONSTRAINT utilisateurs_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.etablissements(id);


--
-- PostgreSQL database dump complete
--

\unrestrict JmYhn2ScGNik79RnDLMzbUmzMuzvxfIo0sywinRcHxJehVfssduKAPe9wiGnqgm

