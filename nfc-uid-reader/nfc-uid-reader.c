#include <stdlib.h>
#include <nfc/nfc.h>
#include <time.h>
#include "zhelpers.h"
#include <unistd.h>

bool nfcread()
{
	nfc_device *pnd;
	nfc_target nt;
	nfc_context *context;
	nfc_init(&context);
	if (context == NULL) {
		printf("Unable to init libnfc (malloc)\n");
		return false;
	}

	pnd = nfc_open(context, NULL);

	if (pnd == NULL) {
		printf("ERROR: %s\n", "Unable to open NFC device.");
		return false;
	}
	if (nfc_initiator_init(pnd) < 0) {
		nfc_perror(pnd, "nfc_initiator_init");
		return false;
	}

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
	const unsigned int maxChars = 14;
	char uid[maxChars], last_uid[maxChars];
	time_t timestamp, last_timestamp;
	
	while (nfc_initiator_select_passive_target(pnd, nmMifare, NULL, 0, &nt) > 0) {
		// wait for nfc message
		const size_t lenUid = nt.nti.nai.szUidLen;
		if (4 == lenUid || 7 == lenUid) 
		{
			const uint8_t *pUid = nt.nti.nai.abtUid;
			// hex to string
			for (i = 0; i < lenUid; ++i)
			{
				sprintf(&uid[i * 2], "%02X", pUid[i]);
			}
			// fill remaining buffer with zeroes
			for (i = lenUid * 2; i < maxChars; ++i)
			{
				uid[i] = 0x00;
			}
			// get current timestamp
			timestamp = time(0);
			// get time interval from last read
			int timespan = timestamp - last_timestamp;
			// only send message if either current uid differs from last uid or debounce timeout exceeded
			if (strncmp(uid, last_uid, maxChars) != 0 || timespan >= 5) 
			{
				// build and send json message
				char* pMsg = (char*)malloc(1024);
				sprintf(pMsg, "{\"trigger\": \"rfid\", \"data\": \"%s\"}", uid);
				s_send(zpublisher, pMsg);
				printf("%s\n", pMsg);
				free(pMsg);
				// store last uid and timestamp
				strncpy(last_uid, uid, maxChars);
				last_timestamp = timestamp;
			}
		}
	}
	nfc_close(pnd);
	nfc_exit(context);
	return true;
}


void main(int argc, const char *argv[])
{
	while(true)
	{
		nfcread();
		usleep(1000000);
	}
