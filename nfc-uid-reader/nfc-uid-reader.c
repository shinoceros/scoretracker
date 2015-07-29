#include <stdlib.h>
#include <nfc/nfc.h>
#include <time.h>
#include "zhelpers.h"

void main(int argc, const char *argv[])
{
	nfc_device *pnd;
	nfc_target nt;
	nfc_context *context;
	nfc_init(&context);
	if (context == NULL) {
		printf("Unable to init libnfc (malloc)\n");
		exit(EXIT_FAILURE);
	}
//	const char *acLibnfcVersion = nfc_version();
	(void)argc;
//	printf("%s uses libnfc %s\n", argv[0], acLibnfcVersion);
	pnd = nfc_open(context, NULL);

	if (pnd == NULL) {
		printf("ERROR: %s\n", "Unable to open NFC device.");
		exit(EXIT_FAILURE);
	}
	if (nfc_initiator_init(pnd) < 0) {
		nfc_perror(pnd, "nfc_initiator_init");
		exit(EXIT_FAILURE);
	}

//	printf("NFC reader: %s opened\n", nfc_device_get_name(pnd));

	const nfc_modulation nmMifare = {
		.nmt = NMT_ISO14443A,
		.nbr = NBR_106,
	};

	// set up zmq
	void *zcontext = zmq_ctx_new();
	void *zpublisher = zmq_socket(zcontext, ZMQ_PUB);
	int rc = zmq_bind(zpublisher, "tcp://127.0.0.1:5556");
	assert (rc == 0);

	size_t i;
	char uid[8], last_uid[8];
	time_t timestamp, last_timestamp;
	
	while (true) {
		// wait for nfc message
		if (nfc_initiator_select_passive_target(pnd, nmMifare, NULL, 0, &nt) > 0) {
			const size_t lenUid = nt.nti.nai.szUidLen;
			if (4 == lenUid && 8 == nt.nti.nai.btSak) {
				const uint8_t *pUid = nt.nti.nai.abtUid;
				// hex to string
				for (i = 0; i < lenUid; ++i) {
					sprintf(&uid[i * 2], "%02X", pUid[i]);
				}
				// get current timestamp
				timestamp = time(0);
				// get time interval from last read
				int timespan = timestamp - last_timestamp;
				// only send message if either current uid differs from last uid or debounce timeout exceeded
				if (strncmp(uid, last_uid, 8) != 0 || timespan >= 5) {
					// build and send json message
					char* pMsg = (char*)malloc(1024);
					sprintf(pMsg, "{\"trigger\": \"rfid\", \"data\": \"%s\"}", uid);
					s_send(zpublisher, pMsg);
					// printf("%s\n", pMsg);
					free(pMsg);
					// store last uid and timestamp
					strncpy(last_uid, uid, 8);
					last_timestamp = timestamp;
				}
			}
		}
	}
	nfc_close(pnd);
	nfc_exit(context);
	exit(EXIT_SUCCESS);
}
